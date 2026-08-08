# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Fixed

- **Regresión real (encontrada antes de desplegar, no en producción):**
  retirar `PublicationRequestStatus.PUBLICADA` en el Incremento 4 rompía
  silenciosamente la columna "Publicadas" de la UI —
  `apiFetch("/publication-requests?estado=publicada")` ahora devuelve
  422 (ese valor ya no existe). `GET /publication-requests` gana un
  parámetro `completa` (filtra por `fecha_cierre is not None`, el
  reemplazo correcto) y `app.js` lo usa en vez del `estado` retirado.
  De paso, `AnalyticsService.solicitudes_pendientes` ahora también
  excluye una solicitud `RECIBIDA` que ya quedó completa sin pasar por
  `aceptar` (posible desde el Incremento 4: un destino Instagram
  confirmado directo sobre una solicitud nunca aceptada) — sin este
  ajuste, esa solicitud se habría quedado marcada "pendiente" para
  siempre.

### Added

- **Sprint 4A, Incremento 7 — MediaAsset (adjuntos de imagen/video)** —
  ver [ADR-007](docs/adr/ADR-007-media-assets.md). Cierra el rollout de
  Sprint 4A. `MediaAsset` pasa de Value Object conceptual (Sprint 3A) a
  entidad hija con tabla propia, mismo tratamiento que `DestinoPublicacion`
  recibió en ADR-006 — necesitaba identidad propia para poder purgar/
  borrar un archivo puntual.
  - Nuevo puerto `MediaStorage` (`guardar`/`leer`/`eliminar`), adaptador
    `LocalDiskMediaStorage` sobre un Railway Volume — elegido sobre S3/R2
    para no requerir cuenta/credenciales nuevas en este incremento; la
    política de retención acota el tamaño acumulado. Swapear a S3/R2 más
    adelante es un adaptador nuevo detrás del mismo puerto, sin tocar
    dominio ni API.
  - `POST/GET/DELETE /publication-requests/{id}/media` y
    `GET .../{media_id}/contenido` (descarga autenticada, streaming — no
    hay URL pública). Subir un archivo se rechaza con 409 una vez la
    solicitud está `completa`; `tipo` (imagen/video) se deriva siempre de
    `content_type`, nunca se confía en un campo separado del cliente.
    Límites por defecto: 10 MB imagen, 200 MB video (`Settings`,
    ajustables).
  - Purga automática: `scripts/purgar_media_expirados.py` (mismo patrón
    operativo que `create_user.py`/`migrate_historical_data.py` — un
    script explícito, no un scheduler dentro del proceso FastAPI) borra
    archivo + fila 7 días (ajustable) después de `fecha_cierre`. Soporta
    `--dry-run`. Idempotente.
  - UI: botón "Media" en cualquier tarjeta (mismo criterio que "Ver
    reporte" — útil en cualquier momento de avance, no solo publicada),
    panel con lista de adjuntos (tipo, nombre, peso, enlace "Ver",
    "Eliminar") y formulario de subida — oculto una vez la solicitud está
    completa, para no toparse con el 409 del backend.
  - Tests: 100% cobertura en entidad, servicio de dominio, adaptador de
    storage, repositorio y script de purga; suite de integración cubre
    subida (imagen/video, 404, tipo no soportado, límite de tamaño
    excedido, 409 sobre solicitud completa), listado, descarga (incluido
    el caso "fila en DB pero archivo ya no está en disco" → 404 en vez de
    500), y borrado. Verificado también de forma interactiva en Chrome
    real: abrir/cerrar el panel, subir, descargar (el navegador renderizó
    el PNG real servido por el endpoint), eliminar — con un error real
    encontrado y corregido en el camino (la migración de `media_assets`
    no se había aplicado todavía a la base de datos local de desarrollo).
    Nueva dependencia de producción: `python-multipart` (requerida por
    FastAPI para `multipart/form-data`).

- **Sprint 4A, Incremento 6 — Reportes automáticos para clientes**: cada
  `PublicationRequest` gana un endpoint de solo lectura,
  `GET /publication-requests/{id}/reporte`, que arma en el momento un
  reporte con enlaces por destino, fecha de publicación, estado y si la
  pauta fue consumida — generación automática, envío manual (compartirlo
  con el cliente sigue siendo una acción humana, no hay integración de
  envío).
  - `core/services/reporte_service.py` (`construir_reporte`) es una
    función pura, sin acceso a repositorios ni red — recibe la
    `PublicationRequest`, sus `DestinoPublicacion` y un `Client | None`
    ya resueltos, y solo da forma a lo que ya le entregaron, la misma
    disciplina que `AnalyticsService` ya sigue.
  - `completa` y `pauta_consumida` se calculan por separado
    deliberadamente: una solicitud puede quedar `completa` (vía
    `esta_completa` sobre sus propios destinos) sin tener nunca una
    `Pauta` vinculada — por ejemplo, una solicitud solo-Instagram — ese
    caso está completo pero no consume cuota, porque no hay `Pauta` de la
    cual consumirla.
  - Tests: 100% cobertura en `reporte_service.py` y el nuevo schema
    `ReporteSolicitudOut`; 5 tests de integración cubren 404, una
    solicitud simple sin destinos, el caso solo-Instagram completo sin
    pauta consumida, el caso con cliente y pauta vía `/publish`, y un
    caso multi-destino no completo con un destino aún pendiente sin
    enlace. Suite completa (`pytest -q`) sigue en verde, sin
    regresiones.
  - UI: botón "Ver reporte" en cualquier tarjeta (pendiente, en curso o
    publicada) — a diferencia del panel de destinos, el reporte es útil
    en cualquier momento de avance, no solo cuando la solicitud ya
    completó. Panel de solo lectura (cliente, pauta consumida, un renglón
    por destino con su enlace) más un botón "Copiar reporte" que arma un
    bloque de texto para pegar a mano en WhatsApp/email — mismo criterio
    "generación automática, envío manual" del endpoint.
    - Encontrado en verificación interactiva (Chrome real): el panel ya
      abierto se quedaba mostrando el estado *antes* del cambio al
      confirmar/cancelar un destino o publicar, porque la cache del
      reporte no se invalidaba junto con la de destinos. Corregido —
      cualquier acción que pueda mover `completa`/`pauta_consumida`
      (agregar destino, crear borrador, confirmar, cancelar, publicar)
      ahora también refresca el reporte si está abierto.

- **Sprint 4A, Incremento 5 — UI de gestión de destinos**: hasta ahora
  todo el trabajo de los Incrementos 3-4 solo era accesible por API.
  Cada tarjeta de una solicitud no completa gana un botón "Destinos"
  que despliega un panel con sus `DestinoPublicacion` (canal, estado,
  acciones) y un selector para agregar uno nuevo — deliberadamente
  limitado a WordPress/Facebook/Instagram en el `<select>` (a pedido del
  negocio: TikTok/YouTube ya existen en `CanalPublicacion` pero no se
  muestran todavía). Por destino: WordPress ofrece "Crear borrador" →
  "Confirmar publicado"; Facebook/Instagram piden pegar el enlace y
  confirmar; cualquiera no publicado se puede cancelar.
  - Una solicitud puede ahora quedar completa **sin pasar por el botón
    "Publicar"** — por ejemplo, contenido que solo va a Instagram nunca
    necesita `aceptar()` ni un destino WordPress. La cola de trabajo
    ("Pendientes") pasó de ser "todo lo `RECIBIDA`" a tres pedidos
    combinados: `estado=recibida` (orden de prioridad, sin cambios),
    `estado=aceptada&completa=false` ("en curso" — ya aceptada, algún
    destino todavía pendiente, antes desaparecía de la vista) y
    `completa=true` ("Publicadas"). Una tarjeta "en curso" ya no ofrece
    Publicar/Vincular/Editar (el triage ya pasó), solo el panel de
    destinos.
  - Verificado dos veces: primero de extremo a extremo por HTTP directo
    (login → cliente → pauta → solicitud → agregar destino Instagram →
    confirmar sin enlace → 422 → confirmar con enlace → 200 → aparece en
    `completa=true`, no en pendientes ni en curso), y después de forma
    interactiva en Chrome real (extensión conectada tras reconectar
    sesión): creación de solicitud, apertura del panel "Destinos",
    selector limitado a WordPress/Facebook/Instagram, agregar Instagram,
    confirmar sin enlace (rechazado visiblemente), confirmar con enlace
    — la tarjeta se movió sola de "Cola de trabajo" a "Publicadas", con
    el borde verde y las métricas del dashboard actualizadas en vivo.
  - Tests: 100% cobertura en el filtro `completa` nuevo y en el ajuste
    de `solicitudes_pendientes`; sin cambios de comportamiento en nada
    que ya funcionaba (suite completa sigue en verde).

- **Sprint 4A, Incremento 4 — Facebook/Instagram, cuota por completitud, y
  el cutover de `PublicationRequestStatus`** — ver
  [ADR-006](docs/adr/ADR-006-multichannel-publication.md), Decisiones 2 y
  3. El cambio de mayor riesgo de negocio de todo el sprint: cambia cómo
  se calcula la cuota consumida de una `Pauta`.
  - `PublicationRequestStatus.PUBLICADA` **retirado**. `estado` vuelve a
    describir solo el triage de intake (`RECIBIDA`/`ACEPTADA`/
    `CANCELADA`) — el mismo rol que `ArticleStatus` cumple para
    `Article` (ADR-002). Si un `PublicationRequest` está "completo" ya
    no depende de `estado`, depende enteramente de sus
    `DestinoPublicacion` vía `esta_completa` (Incremento 1).
  - `PautaService.publicaciones_consumidas`/`publicaciones_restantes`/
    `cuota_agotada` ganan un parámetro `destinos` obligatorio (sin
    default deliberadamente, para que un caller que lo olvide falle en
    build/test en vez de reportar cuota en cero silenciosamente) y
    cuentan por `esta_completa`, no por `estado == PUBLICADA`.
    `AnalyticsService`/`DecisionEngineService` ganan el mismo parámetro
    `destinos` en su constructor y lo propagan a cada llamada a
    `PautaService`.
  - `core.services.publication_request_service.aceptar` reemplaza a
    `mark_as_published` — transiciona `estado` a `ACEPTADA` (mismo
    invariante de `pauta_id` obligatorio que ya tenía `PUBLICADA`).
  - `POST /publication-requests/{id}/publish` (el botón "Publicar" que
    ya se usa a diario) mantiene su comportamiento visible **sin
    cambios**: acepta la solicitud y crea/reutiliza un destino WordPress
    marcado `PUBLICADO` — el operador no nota diferencia, mismos números
    de cuota, mismas validaciones (`422` sin pauta).
  - `POST /publication-requests/{id}/destinos/{destino_id}/confirmar-publicacion`
    (Facebook/Instagram registran su `url_publicacion` aquí — obligatoria
    para esos dos canales, la entidad la exige; WordPress solo confirma)
    y `POST .../cancelar` (cancela un destino que nunca salió, incluido
    uno `FALLIDO` — nunca debe quedar sin salida). Ambos recalculan
    `esta_completa`/`fecha_cierre` sobre el conjunto completo de destinos
    de la solicitud, no solo el que cambió.
  - **Migración de datos** (`a1b2c3d4e5f6`, sin cambios de esquema):
    reescribe cada fila `estado='publicada'` existente a `estado='aceptada'`
    + un `DestinoPublicacion(canal='wordpress', estado='publicado')` nuevo
    — la forma exacta que produce el flujo de compatibilidad de arriba,
    así el cálculo de cuota da el mismo número antes y después. Probada
    con datos sembrados localmente: ciclo completo `upgrade` →
    `downgrade` → `upgrade`, verificado que la app lee los datos
    migrados sin error y que `publicaciones_consumidas`/`restantes` no
    cambian. `scripts/migrate_historical_data.py` (la fuente real de los
    datos de producción) actualizado para producir esta forma
    directamente en importaciones futuras.
  - Tests: 100% cobertura en endpoints nuevos; suite completa reescrita
    donde `estado=PublicationRequestStatus.PUBLICADA` se usaba como
    atajo para "esto cuenta para la cuota" — ahora construye un
    `DestinoPublicacion` real.

- **Sprint 4A, Incremento 3 — integración real con WordPress (creación
  automática de borradores)**: ver
  [ADR-006](docs/adr/ADR-006-multichannel-publication.md), Decisión 4.
  - `agents/wordpress/client.py` (`WordPressCMSPublisher`): primer
    adaptador real de `core.ports.cms_publisher.CMSPublisher` —
    autentica con un Application Password de WordPress (nunca la
    contraseña de la cuenta) vía HTTP Basic Auth contra
    `/wp-json/wp/v2/posts`, siempre con `status=draft`. Nunca publica —
    docs/PROJECT_RULES.md regla 1.
  - `CMSPublisher.create_draft` cambia su tipo de retorno de `str` a
    `CMSDraftResult` (`post_id` + `url`) — corrección a ADR-006 (decía
    "sin modificarlo"), sin riesgo real porque ningún adaptador existía
    todavía.
  - `core.services.wordpress_publication_service`: `construir_contenido_wordpress`
    (arma `{title, content}` desde una `PublicationRequest`, usando
    `titulo` o los primeros 60 caracteres de `texto` si no hay título) y
    `crear_borrador` (llama al `CMSPublisher` inyectado, adjunta
    `wp_post_id`/`wp_url` al `DestinoPublicacion` sin cambiar su
    `estado` — crear un borrador no es lo mismo que publicar).
  - API: `POST /publication-requests/{id}/destinos` (crear un destino),
    `GET .../destinos` (listar), `POST
    .../destinos/{destino_id}/crear-borrador-wordpress` (dispara la
    creación real del borrador). Nuevos manejadores de excepción:
    `WordPressConfigurationError` → 503 (credenciales no configuradas),
    `requests.RequestException` → 502 (WordPress inalcanzable o
    rechazó la solicitud).
  - `WORDPRESS_SITE_URL`/`WORDPRESS_USERNAME`/`WORDPRESS_APP_PASSWORD`
    ya estaban declaradas en `config/settings.py` y `.env.example` desde
    el sprint de Foundation (para "el futuro agente WordPress") — este
    incremento es el primero en usarlas de verdad.
  - Tests: 100% cobertura en todo el código nuevo. Los tests de API
    fuerzan explícitamente un `Settings()` sin configurar en el caso
    503 (nunca dependen del `.env` real del entorno) precisamente para
    que correr la suite no pueda disparar una llamada real contra un
    sitio WordPress de producción.

- **Sprint 4A, Incremento 2 — título en el formulario de solicitudes**:
  campo `titulo` expuesto de punta a punta — `POST /publication-requests`
  lo acepta (opcional), `PATCH /{id}` lo edita mientras la solicitud siga
  `RECIBIDA` (misma regla que ya aplica a `texto`/`prioridad_manual`, vía
  `edit_solicitud` ampliado), `GET` lo devuelve. UI (`app/api/static/`):
  campo "Título (opcional)" en el formulario de creación y en el form de
  edición inline de cada tarjeta; se muestra en negrita sobre el texto
  cuando está presente. Verificado extremo a extremo sobre HTTP real
  (crear con título, editarlo, confirmarlo en el listado) contra un
  usuario de prueba local — la extensión de navegador no estaba
  disponible en este entorno para una verificación visual interactiva.
  Tipo de contenido queda fuera de alcance, como ya fijó
  [ADR-006](docs/adr/ADR-006-multichannel-publication.md).

- **Sprint 4A, Incremento 1 — modelo de dominio multicanal**: primer paso
  de la reestructuración de Solicitudes de Publicación hacia contenido
  reutilizable con múltiples destinos — ver
  [ADR-006](docs/adr/ADR-006-multichannel-publication.md) para el diseño
  completo y `docs/product/DOMAIN_MODEL.md` para el modelo actualizado.
  Puramente aditivo: ningún endpoint, servicio o comportamiento existente
  cambia — el botón "Publicar" y el cálculo de cuota de `PautaService`
  siguen funcionando exactamente igual que antes de este incremento.
  - `core.entities.destino_publicacion.DestinoPublicacion` (+
    `CanalPublicacion`: `WORDPRESS`/`FACEBOOK`/`INSTAGRAM`, `EstadoDestino`:
    `PENDIENTE`/`PUBLICADO`/`FALLIDO`/`CANCELADO`) — una fila por
    `(solicitud, canal)`, cada una con su propio ciclo de vida.
  - `core.services.destino_publicacion_service`: `marcar_publicado`,
    `marcar_fallido`, `cancelar` (transiciones inmutables) y
    `esta_completa` — la condición derivada, nunca almacenada, que
    determina si una solicitud terminó de distribuirse en todos sus
    destinos.
  - `PublicationRequest` gana `titulo` y `fecha_cierre` (ambos
    opcionales, sin uso todavío por ningún endpoint) y
    `core.services.publication_request_service.cerrar_si_completa`, que
    asigna `fecha_cierre` una sola vez, la primera vez que
    `esta_completa` es verdadero — mismo patrón de timestamp de
    auditoría que `Pauta.fecha_registro`.
  - **`PublicationRequestStatus` NO se reduce en este incremento** —
    `PUBLICADA` se mantiene, a diferencia de lo previsto originalmente en
    ADR-006 Decisión 5: retirarla ahora habría roto
    `PautaService.publicaciones_consumidas` y, en cascada,
    `AnalyticsService`, `decision_engine` y las rutas de dashboard/
    insights (30 archivos referencian estos conceptos) sin la validación
    contra datos reales que la propia Decisión 3 del ADR exige antes de
    ese cambio. Ese cutover queda confirmado para el Incremento 4, no
    este.
  - Persistencia: `DestinoPublicacionModel` (tabla nueva
    `destinos_publicacion`, FK a `publication_requests` y a `users`),
    `SqlAlchemyDestinoPublicacionRepository`,
    `core.ports.destino_publicacion_repository.DestinoPublicacionRepository`;
    `UnitOfWork` gana `destinos_publicacion`. Migración
    `15f24c0ea8ef` (aditiva: agrega `titulo`/`fecha_cierre` nullable a
    `publication_requests`, crea `destinos_publicacion`), verificada con
    un ciclo completo `upgrade` → `downgrade` → `upgrade` y `alembic
    check` sin drift.
  - Mismo hallazgo de orden de inserción que ya documentó el Login MVP
    (`sessions`/`users`): `destinos_publicacion` ordena alfabéticamente
    antes que `publication_requests`, así que guardar ambas filas nuevas
    en un solo `commit()` sin `flush()` intermedio falla por FK — resuelto
    en los fixtures de test de la misma forma, sin afectar código de
    producción.
  - Cobertura 100% en todo el código nuevo/modificado de este incremento.

### Fixed

- **Primer deploy real a Railway, 2 fallos encontrados y corregidos en el camino:**
  - Railway usaba su builder automático (Railpack), no
    `docker/Dockerfile` — no lo detecta fuera de la raíz del repo.
    Railpack falló con "No start command detected" al no poder adivinar
    `alembic upgrade head && uvicorn app.api.main:app`. Corregido con
    `railway.json` (`build.dockerfilePath: "docker/Dockerfile"`),
    versionado en el repo — no una configuración manual en el dashboard
    que nadie recordaría después.
  - Con el Dockerfile ya en uso, el deploy siguiente falló distinto:
    `ModuleNotFoundError: No module named 'psycopg2'`. La
    `DATABASE_URL` interna real de Railway
    (`${{Postgres.DATABASE_URL}}`) usa el esquema `postgresql://`, no
    el legacy `postgres://` que `normalize_database_url` ya sabía
    reescribir — sin driver explícito, SQLAlchemy 2.0 cae por defecto a
    `psycopg2`, no instalado (el proyecto usa `psycopg` v3). La función
    ahora reescribe cualquier esquema `postgres://`/`postgresql://` sin
    driver a `postgresql+psycopg://`, dejando intactos los que ya
    especifican uno (`+psycopg`, `+asyncpg`, ...).
  - El test existente de `normalize_database_url` traía la expectativa
    **incorrecta** para el caso `postgresql://` (afirmaba que se
    quedaba igual) desde que se escribió en Sprint 3C — nunca corrió
    contra una URL real de Railway hasta este deploy. Corregido, y se
    agregó el caso `+asyncpg` para blindar contra la próxima variante.

### Added

- **Login MVP**: autenticación con sesiones server-side, reincorporada
  al alcance del MVP tras el deploy a Railway con datos sensibles de
  clientes en una URL pública — ver
  [ADR-005](docs/adr/ADR-005-authentication.md) para el razonamiento
  completo y qué queda explícitamente fuera (invitaciones, reset de
  contraseña, 2FA, bloqueo por intentos fallidos, SMTP, gestión avanzada
  de usuarios).
  - `core.entities.user.User`, `core.entities.session.Session` — la
    sesión es server-side (Postgres), no JWT: revocar una sesión
    específica es un `DELETE` inmediato.
  - `core.ports.password_hasher.PasswordHasher` (`Protocol`) +
    `security/password_hasher.py` (paquete nuevo, par de `database/`):
    `Argon2IdPasswordHasher` sobre `argon2-cffi` — Argon2id nunca entra a
    `core/`, misma disciplina que ya aplica a SQLAlchemy.
  - `core.ports.user_repository.UserRepository`,
    `core.ports.session_repository.SessionRepository` +
    implementaciones SQLAlchemy; `UnitOfWork` gana `users`/`sessions`.
    Migración nueva (`users`, `sessions` con FK a `users.id`).
  - `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
    (`app/api/routers/auth.py`). El login corre una verificación Argon2
    contra un hash señuelo real cuando el email no existe, para que el
    tiempo de respuesta no delate qué emails tienen cuenta.
  - Todos los endpoints existentes (`/clients`, `/pautas`,
    `/publication-requests`) protegidos vía
    `APIRouter(dependencies=[Depends(get_current_user)])` — a nivel de
    router, no por función, para que cualquier endpoint agregado después
    quede protegido automáticamente.
  - `scripts/create_user.py`: única forma de crear una cuenta (sin
    invitaciones ni endpoint de gestión) — idempotente, contraseña
    siempre por prompt interactivo, nunca por argumento de línea de
    comandos.
  - UI (`app/api/static/`): pantalla de login, botón de cerrar sesión;
    `apiFetch` redirige a la pantalla de login automáticamente ante
    cualquier 401 (sesión ausente o vencida en cualquier momento del uso,
    no solo al cargar la app).
  - `tests/integration/api/conftest.py`: el fixture `client` ahora se
    autentica automáticamente (usuario de prueba real + login real vía
    `POST /auth/login`) — **ningún test de sprints anteriores necesitó
    cambiar su código**, solo heredó el nuevo comportamiento del fixture.
    `unauthenticated_client` queda disponible para los tests que
    verifican específicamente el rechazo sin sesión.
  - Hallazgo real durante las pruebas de persistencia: sin
    `relationship()` a nivel ORM entre `UserModel`/`SessionModel`
    (mapeados como columnas FK simples, igual que el resto de
    `database/models/`), SQLAlchemy no puede ordenar automáticamente sus
    inserts dentro de un mismo `flush()` — y el orden alfabético de las
    tablas (`sessions` antes que `users`) resulta ser el incorrecto. El
    mismo patrón en `Client`→`Pauta`→`PublicationRequest` funcionaba por
    coincidencia alfabética, no porque el problema no existiera.
    Documentado y resuelto con un `flush()` explícito en los fixtures de
    test — no afecta código de producción, que nunca crea dos entidades
    nuevas relacionadas antes de un mismo `commit()`.
  - `argon2-cffi` agregado a `requirements.txt`.
  - `docs/product/MVP_SCOPE.md` actualizado: autenticación pasa de
    "fuera del MVP" a "dentro, alcance mínimo".

### Fixed

- **`docker/Dockerfile` no levantaba la aplicación real.** Desde que
  existe `app/api/` (Sprint 3D), el `CMD` seguía apuntando a
  `python -m app.main` — el smoke test de configuración/logging de la
  Fase 0, que no sirve ni la API ni la UI. Encontrado al preparar el
  deploy a Railway. Ahora el contenedor aplica las migraciones de
  Alembic y arranca uvicorn contra `app.api.main:app`, escuchando en
  `$PORT` (Railway lo inyecta; local usa 8000 por default). Se usa
  `python -m alembic` / `python -m uvicorn`, no los scripts de consola
  `alembic`/`uvicorn` directos — su presencia en el `PATH` depende de
  cómo los instale `pip`, `python -m` no. Verificado ejecutando la
  cadena exacta del `CMD` fuera de Docker (no disponible en este
  entorno) contra una base SQLite descartable: migra y responde `200`
  en `/ui/`.
  - `docker-compose.yml`: agrega el mapeo de puerto `8000:8000` (antes
    ausente — ni con el `Dockerfile` corregido hubiera sido alcanzable
    desde `localhost`) y corrige el comentario sobre PostgreSQL, que
    ya no requiere un servicio `db` local (`DATABASE_URL` decide SQLite
    vs. Postgres sin cambiar código, ver Sprint 3C).

### Added

- **`Pauta.peso_comercial` (Sprint 3G)**: propiedad nueva —
  `valor_pagado / publicaciones_contratadas`, redondeado a 2 decimales
  con `ROUND_HALF_UP` explícito (no el `ROUND_HALF_EVEN` por defecto de
  `Decimal.quantize()`). Expuesta en `PautaOut`
  (`GET /pautas`, `GET /pautas/{id}`) sin persistirse — se recalcula en
  cada respuesta, igual que el resto de los campos derivados de `Pauta`.
  No se usa todavía para ordenar la cola de solicitudes; eso queda para
  cuando se defina la estrategia de priorización completa.
  - **Decisión arquitectónica deliberada:** a diferencia de todo lo demás
    calculado sobre `Pauta` (que vive en
    `core.services.pauta_service.PautaService`), `peso_comercial` es un
    método de la propia entidad. Justificación completa en el docstring
    de la propiedad (`core/entities/pauta.py`): no necesita reloj ni el
    historial de `PublicationRequest` de otro agregado — es una función
    pura de los propios campos de `Pauta`, ya protegidos por su propio
    invariante (`publicaciones_contratadas > 0`). Es una excepción
    puntual y documentada al estilo "entidades sin comportamiento" del
    proyecto, no todavía una regla general — se posterga
    deliberadamente un ADR formal hasta validar el criterio en más
    sprints; si aparecen más propiedades derivadas de este tipo, se
    documentará el principio general entonces, no este caso aislado.

- **Mejoras UX P0 (Sprint 3F)**: los 5 hallazgos P0 de
  `docs/ux/sprint-3d5-ux-review.md`, implementados solo en
  `app/api/static/` (HTML/CSS/JS) — cero cambios de backend, dominio o
  reglas de negocio; los umbrales nuevos son decisiones de presentación,
  no persisten en ningún lado ni afectan a la API.
  - Barra de resumen (`#resumen`) visible en ambas pestañas: solicitudes
    pendientes, pautas por vencer (≤7 días) y cupos agotados —
    recalculada en cada carga de datos.
  - Badges nuevos en la pestaña Clientes y Pautas: "vence en Nd" (además
    del "vencida" existente) y "cupo bajo (N)" (≤2 restantes, distinto de
    "cupo agotado", que ya existía).
  - Solicitudes con ≥4 horas esperando se resaltan en la cola (ícono de
    reloj + borde de color) — no bloquean ni alteran el orden, solo
    llaman la atención.
  - "Nuevo cliente" y "Nueva pauta" ahora son `<details>` colapsados por
    defecto (se re-colapsan solos tras crear con éxito), para que la
    lista de clientes sea lo primero visible en esa pestaña.
  - Verificado con datos reales contra el servidor corriendo (pauta a 3
    días de vencer, pauta con 2 restantes, pauta agotada, solicitud
    reforzada 6h atrás directamente en la base para simular espera) — la
    extensión de navegador se desconectó a mitad de la verificación
    (requiere reautenticación, ajeno a este cambio) así que la
    confirmación final se hizo ejecutando la lógica real de `app.js`
    (extraída del archivo que el servidor sirve, no una reimplementación)
    contra las respuestas reales de la API en Node, más inspección directa
    del HTML/CSS servidos.
  - Con este sprint se cierra el desarrollo de funcionalidades nuevas a
    propósito: el sistema queda en uso real varios días antes de
    continuar con las mejoras P1, WhatsApp, IA o automatizaciones.

- **Cerrar el flujo operativo: vincular pauta (Sprint 3E)**: una
  `PublicationRequest` recibida sin `Pauta` ahora puede vincularse
  después, antes de aceptarse/publicarse — el hallazgo P2 más importante
  de `docs/ux/sprint-3d5-ux-review.md`, cerrado antes de continuar con
  las mejoras visuales (P0/P1) de ese mismo documento.
  - `core.services.publication_request_service.link_pauta`: transición
    inmutable que fija `pauta_id` sin tocar `estado` — cero reglas de
    negocio nuevas, mismo patrón que `mark_as_published`.
  - `POST /publication-requests/{id}/link-pauta` (`pauta_id` en el
    cuerpo) — 404 si la solicitud no existe, 400 si la pauta no existe
    (constraint de FK, mismo mecanismo que el resto de la API), 200 con
    la solicitud actualizada.
  - UI: las filas de la cola sin pauta ahora muestran un selector +
    botón "Vincular" en vez de un botón "Publicar" deshabilitado; al
    vincular, la fila se refresca y el botón "Publicar" queda
    disponible. Verificado en navegador real: solicitud sin pauta →
    vincular → publicar → cupo restante de la pauta baja correctamente.
  - Deliberadamente fuera de este sprint: la barra de resumen, los
    badges "por vencer", el resaltado de solicitudes urgentes y los
    formularios colapsados (P0/P1 de la revisión UX) — quedan para el
    siguiente sprint, ahora que el flujo que representan está completo.

- **Excel-replacement UI (Sprint 3D-UI)**: interfaz mínima en
  `app/api/static/` — una sola página HTML, sin framework ni build step,
  servida por el mismo FastAPI en `/ui/` (sin CORS). Dos pantallas: **Cola
  de Solicitudes** (registrar, ver pendientes, publicar) y **Clientes y
  Pautas** (crear cliente, crear pauta, ver cupo/vigencia por cliente).
  Probado de punta a punta en un navegador real: crear cliente → crear
  pauta → registrar 1 solicitud → publicarla → confirmar que el cupo
  restante bajó de 10/10 a 9/10.
  - Se descubrió que la API (Sprint 3D) no tenía ningún endpoint de
    lectura en lista — solo creación y `GET /pautas/{id}` uno por uno.
    Sin eso, ninguna pantalla podía mostrar qué existe. Se agregaron
    exactamente 3, autorizados explícitamente antes de implementarlos:
    `GET /clients`, `GET /pautas` (con cupo/vigencia calculados,
    reutilizando `PautaService`), `GET /publication-requests` (filtro
    opcional `estado`). Ningún otro endpoint resultó necesario.
  - Nuevo en los puertos/repositorios: `ClientRepository.list_all`,
    `PublicationRequestRepository.list_all(estado=None)` — puro acceso de
    lectura sobre datos ya existentes, cero reglas de negocio nuevas.
    `PautaRepository.list_all` ya existía desde Sprint 3C, sin cambios.
  - `GET /` redirige a `/ui/` para que abrir la URL base ya muestre la
    interfaz.

- **Internal API (Sprint 3D)**: API REST mínima en `app/api/` sobre el
  Commercial Core (`Client`, `Pauta`, `PublicationRequest`) — primera
  forma de operar el dominio sin escribir Python. Sin autenticación, sin
  permisos, sin paginación, sin filtros avanzados, sin OpenAPI
  personalizado (docs automáticas de FastAPI en `/docs`, sin tocar).
  - `POST /clients`, `POST /pautas`, `GET /pautas/{id}` (con
    `publicaciones_consumidas`/`restantes`/`vigente`/`vencida`/
    `cuota_agotada` calculados vía `PautaService`, sin lógica nueva),
    `POST /publication-requests`.
  - `POST /publication-requests/{id}/publish`: no estaba en la lista
    literal del sprint, pero sin ella `GET /pautas/{id}` nunca mostraría
    cupo consumido — expone `mark_as_published` (Sprint 3B), cero lógica
    de dominio nueva.
  - `app/api/dependencies.py`: un `UnitOfWork` por request vía FastAPI
    `Depends`; `app/api/errors.py`: `ValueError` de una entidad → 422,
    `IntegrityError` de una FK violada → 400, sin try/except repetido en
    cada handler.
  - `database/engine.py`: `enable_sqlite_foreign_keys` — SQLite no aplica
    llaves foráneas por defecto (a diferencia de Postgres); sin esto, un
    `client_id`/`pauta_id` inválido pasaría silencioso en dev/tests y
    fallaría recién en producción. Esto rompió cuatro tests de Sprint 3C
    que usaban IDs inventados sin fila real — se corrigieron para crear
    las entidades padre de verdad, como ya haría Postgres.
  - `fastapi`, `uvicorn[standard]` en `requirements.txt`; `httpx` (para
    `TestClient`) en `requirements-dev.txt`.
  - `tests/integration/api/`: un test por endpoint más un flujo completo
    de extremo a extremo por HTTP (crear cliente → pauta → 3 solicitudes
    → publicar 2 → verificar 8 restantes) — el mismo escenario de la
    Definición de Terminado de Sprint 3B, ahora sobre HTTP real.

- **Persistence Layer (Sprint 3C)**: `Client`, `Pauta` y `PublicationRequest`
  ahora se pueden persistir en PostgreSQL (Railway) o SQLite, sin cambiar
  el dominio.
  - `core/ports/`: `ClientRepository`, `PautaRepository` (+ `list_all`),
    `PublicationRequestRepository` (+ `list_by_pauta_id`) — contratos
    mínimos, cada método respaldado por una necesidad real del dominio, no
    heredan del `Repository[T]` genérico (reservado para Discovery).
    `UnitOfWork` (`ABC`, no `Protocol` — comparte lógica real de
    commit/rollback en la clase base).
  - `database/models/`: `ClientModel`, `PautaModel`,
    `PublicationRequestModel` — mapeos SQLAlchemy 2.0 (Declarative
    Mapping), completamente separados de las entidades de dominio;
    `pauta_id` nullable, reflejando el ajuste de Sprint 3B.1. `tipo`/
    `estado` se guardan como `String` simple, nunca `ENUM` nativo de
    Postgres (evita migraciones costosas al agregar un valor nuevo).
  - `database/repositories/`: `SqlAlchemyClientRepository`,
    `SqlAlchemyPautaRepository`, `SqlAlchemyPublicationRequestRepository`
    — traducen entidad ↔ modelo ORM.
  - `database/unit_of_work.py`: `SqlAlchemyUnitOfWork` — una transacción
    por bloque `with`, rollback automático al salir salvo `commit()`
    explícito.
  - `database/engine.py`: `normalize_database_url` — reescribe
    `postgres://` (lo que Railway entrega) a `postgresql+psycopg://` (lo
    que SQLAlchemy 2.0 requiere).
  - Alembic inicializado en `database/migrations/`; migración inicial
    generada y verificada con un ciclo completo `upgrade head` →
    `downgrade base` → `upgrade head` (reconstruye el esquema desde cero)
    y `alembic check` (sin drift entre modelos y migración).
  - `psycopg[binary]` agregado a `requirements.txt`.
  - Motor síncrono, no asíncrono — decisión explícita: nada en el proyecto
    hoy es async (agentes, `DiscoveryEngine`, futuro `app/`), y no hay
    carga concurrente que lo justifique.
  - Tests de persistencia (`tests/integration/persistence/`) corren
    contra SQLite local, no contra Railway real — sin acceso a esas
    credenciales desde este entorno. El esquema evita deliberadamente
    cualquier característica exclusiva de Postgres para que el mismo
    código se comporte igual en ambos.

### Changed

- **Domain Adjustment (Sprint 3B.1)**: `PublicationRequest.pauta_id` pasa
  de obligatorio a opcional (`str | None`). Ahora puede existir una
  solicitud sin `Pauta` asignada mientras esté en `RECIBIDA` o
  `CANCELADA` — la obligatoriedad se traslada al momento de pasar a
  `ACEPTADA` o `PUBLICADA`, validado por la propia entidad. Corrige la
  discrepancia señalada en la revisión de dominio de Sprint 3B: el modelo
  anterior no podía representar el caso operativo más común (un mensaje
  de WhatsApp de un remitente aún sin vincular a un cliente).

### Added

- **Commercial Core MVP (Sprint 3B)**: primer código real del dominio
  comercial, reemplaza al Excel que usa hoy Portal Vallenato para
  controlar pautas. Basado en Domain Discovery sobre reglas de negocio
  reales, no en el diseño especulativo de Sprint 3A (ver nota en
  "Changed" abajo).
  - `core.entities.client.Client` (+ `ClientType`): el cliente comercial
    (artista, manager, promotor, empresario).
  - `core.entities.pauta.Pauta`: un período comercial contratado —
    cantidad de publicaciones, fecha de inicio/fin propias del cliente
    (nunca calendario), valor y fecha de pago.
  - `core.entities.publication_request.PublicationRequest` (+
    `PublicationRequestStatus`): una solicitud recibida por WhatsApp,
    vinculada a una `Pauta`. Sin adjuntos todavía (sprint futuro).
  - `core.services.pauta_service.PautaService`: publicaciones
    consumidas/restantes, vigencia/vencimiento y cuota agotada de una
    `Pauta` — todo calculado a partir del historial de
    `PublicationRequest`, nunca un contador almacenado. Reloj inyectable
    para tests, mismo patrón que `DiscoveryEngine`.
  - `core.services.publication_request_service.mark_as_published`: la
    transición de estado inmutable de una `PublicationRequest`.
  - Tests unitarios (entidades + servicios) e integración
    (`tests/integration/test_commercial_core_scenario.py`, el escenario
    completo de la Definición de Terminado del sprint) — 100% de
    cobertura en todo el código nuevo, mismo estándar que Discovery
    Engine (Sprint 2).
- Reposicionamiento comercial (Sprint 3A): la mayoría de las publicaciones
  de Portal Vallenato no se originan en Discovery, llegan por WhatsApp de
  managers, artistas y empresas. Documentado en
  [ADR-003](docs/adr/ADR-003-publication-inbox.md) (bounded context
  **Publication Inbox**, entidad `PublicationRequest` como convergencia de
  cualquier canal de entrada) y
  [ADR-004](docs/adr/ADR-004-commercial-manager.md) (bounded context
  **Commercial Manager**: `Client`, `CommercialContact`, `Contract`,
  `Plan`, `Campaign`, `PublicationRegistryEntry`, `Alert`).
- `docs/architecture/publication-inbox.md` y
  `docs/architecture/commercial-manager.md`: diseño técnico de ambos
  bounded contexts.
- `docs/business/commercial-workflow.md`: el flujo comercial visto desde
  negocio, complementa a `docs/business/editorial-workflow.md`.
- `agents/whatsapp/README.md`: placeholder documentado para el futuro
  agente/canal WhatsApp.
- `docs/ROADMAP.md` (Fase 1.5) y `docs/roadmap/v1-roadmap.md`: seis
  sprints nuevos (Commercial Manager Core, Commercial Dashboard,
  Publication Inbox Core, Radar → Publication Inbox, WhatsApp Channel,
  Commercial Registry Wiring), en ese orden — núcleo comercial y su
  dashboard antes que las integraciones de canal.
- `docs/product/DOMAIN_MODEL.md`: entidades `PublicationRequest`,
  `MediaAsset`, `Client`, `CommercialContact`, `Contract`, `Plan`,
  `Campaign`, `PublicationRegistryEntry`, `Alert`, con la disambiguación
  explícita `Client` vs. `MediaOutlet`.
- `docs/product/MVP_SCOPE.md`: Commercial Manager y Publication Inbox
  entran al alcance del MVP de Portal Vallenato (sin introducir
  multi-tenencia — ver ADR-004, Decisión 1).

### Changed

- **Nota de divergencia (Sprint 3B):** el código de Commercial Core MVP
  descrito arriba implementa un dominio más simple que el diseñado en
  Sprint 3A / ADR-003 / ADR-004. `CommercialContact`, `Contract`, `Plan`,
  `Campaign`, `Alert` y "Publication Inbox" como bounded context
  multicanal **no se implementaron** — no tenían respaldo en las reglas
  de negocio reales relevadas en Domain Discovery (Sprint 3B). Los ADR-003
  y ADR-004, y la documentación que actualizan, describen una fase de
  diseño ya superada por el código; quedan como registro histórico, no
  como especificación vigente. Actualizar esa documentación queda
  pendiente de un sprint dedicado a ese fin.
- `docs/VISION.md`, `docs/product/PRODUCT_VISION.md`,
  `docs/business/editorial-workflow.md`,
  `docs/architecture/system-overview.md`, `docs/ARCHITECTURE.md`,
  `agents/radar/README.md` y `README.md` anotados (sin reescribir su
  contenido original) para reflejar que Radar es uno de varios canales de
  entrada, no el único.

## [0.3.0] - 2026-07-08

### Added

- Entidades de dominio en `core/entities/`: `NewsCandidate`, `Source`,
  `Article` (con `ArticleStatus`), `EditorialTask` (con
  `EditorialTaskStatus`) — dataclasses inmutables, sin dependencias
  externas.
- `core.services.deduplication.generate_candidate_hash`: huella de
  contenido usada para deduplicar candidatos.
- `core.services.discovery_engine.DiscoveryEngine`: agrega, deduplica por
  hash y ordena candidatos de varias fuentes; devuelve un evento
  `NewsFound`.
- `tests/fakes/FakeContentSource`: doble de prueba que lee fixtures JSON
  en lugar de la red, implementando `core.ports.content_source.ContentSource`.
- `tests/fixtures/{silvestre,churo,festival}.json`: noticias vallenatas de
  ejemplo, con un duplicado intencional para probar la deduplicación.
- 41 pruebas nuevas (unitarias sobre entidades/servicios con dobles en
  memoria, de integración sobre fixtures reales). 100% de cobertura sobre
  el código nuevo de este sprint.
- `exclude_lines` en `[tool.coverage.report]` (`pyproject.toml`) para no
  penalizar cuerpos de método de `Protocol` (nunca se ejecutan
  directamente) en el cálculo de cobertura.

### Changed

- `core.ports.content_source.ContentSource`: `fetch_new_references() ->
  list[str]` pasa a ser `fetch_candidates() -> list[NewsCandidate]`, y
  gana una propiedad `source: Source`. Ningún adaptador implementaba
  todavía este port, así que no rompe nada en ejecución — es la
  formalización que el propio docstring del port anticipaba desde Sprint 1.
- `core.events.news_found.NewsFound` pasa de ser una clase vacía a tener
  payload real (`candidates`, `occurred_at`).

## [0.2.0] - 2026-07-07

### Added

- `core/events/`: espacio reservado para eventos de dominio (`NewsFound`,
  `ArticleRewritten`, `DraftCreated`, `NotificationRequested`) — clases
  vacías y documentadas, sin comportamiento ni event bus todavía.
- `core/services/`: espacio reservado para servicios de dominio, con
  `README.md` explicando qué pertenece y qué no pertenece ahí.
- `requirements-dev.txt`: dependencias de desarrollo (testing, lint,
  tipado) separadas de `requirements.txt` (producción).
- Configuración de `coverage` (`pytest-cov`) en `pyproject.toml`.
- Plugin de mypy para Pydantic (`pydantic.mypy`) en `pyproject.toml`.
- Sección "Para desarrolladores nuevos" en `README.md` con ruta de lectura
  y guía de "dónde poner código nuevo".
- Regla de estilo contra módulos `utils.py`/`helpers.py` genéricos y
  convenciones de nombrado para eventos y servicios de dominio en
  `docs/CODING_STANDARDS.md`.
- Sección "Eventos de dominio (preparado, no implementado)" en
  `docs/ARCHITECTURE.md`.

### Changed

- `requirements.txt` ya no incluye herramientas de desarrollo (`pytest`,
  `ruff`, `mypy`) — antes se instalaban también en la imagen Docker de
  producción sin necesidad.
- `docker/Dockerfile` ahora instala una imagen de producción más liviana
  como efecto de lo anterior (sin cambios en el propio Dockerfile).

### Fixed

- Referencias desactualizadas en `README.md` (`core/` ya no se describía
  con precisión tras esta revisión).

## [0.1.0] - 2026-07-07

### Added

- Estructura base del proyecto (Prompt 001 — Foundation): `app/`, `core/`,
  `agents/`, `workflows/`, `database/`, `config/`, `shared/`, `prompts/`,
  `scripts/`, `tests/`, `docs/`, `docker/`, `logs/`.
- Esqueleto de arquitectura hexagonal: contratos (`Protocol`) en
  `core/ports/` y excepciones de dominio en `core/exceptions.py`.
- Paquetes placeholder documentados para los futuros agentes: Radar,
  Extractor, Writer, SEO, Images, WordPress, Telegram, Scheduler, Social,
  Analytics y AI Orchestrator.
- Configuración centralizada vía `config/settings.py` (Pydantic Settings +
  `.env`).
- Logging centralizado vía `shared/logger.py`.
- Scaffolding de base de datos (engine y sesión de SQLAlchemy) en
  `database/`, sin modelos todavía.
- Configuración de Docker (`docker/Dockerfile`, `docker-compose.yml`).
- Documentación de proyecto: `README.md`, `VISION.md`, `ROADMAP.md`,
  `ARCHITECTURE.md`, `PROJECT_RULES.md`, `CODING_STANDARDS.md`,
  `CONTRIBUTING.md`.
- Suite inicial de pruebas (`pytest`) validando la carga de configuración.

[Unreleased]: https://example.invalid/compare/v0.3.0...HEAD
[0.3.0]: https://example.invalid/compare/v0.2.0...v0.3.0
[0.2.0]: https://example.invalid/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.invalid/releases/v0.1.0
