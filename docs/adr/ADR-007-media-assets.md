# ADR-007: `MediaAsset` — adjuntos de una `PublicationRequest`, almacenamiento y purga

- **Estado:** Aceptado
- **Fecha:** 2026-08-07 (Sprint 4A — Incremento 7, el último del rollout
  acordado en [ADR-006](ADR-006-multichannel-publication.md), Decisión 5)
- **Contexto del documento:** ver [ADR-001](ADR-001-project-vision.md)
  para las convenciones de formato. Cierra el punto que ADR-006 dejó
  explícitamente fuera de su alcance ("Multimedia (`MediaAsset`, storage
  temporal, purga) queda fuera de alcance de este ADR — se diseña en su
  propio momento, Incremento 6"; ese incremento se renumeró a 7 en el
  tracker de trabajo tras insertar la UI de destinos, ver `CHANGELOG.md`).

## Contexto

Una `PublicationRequest` hoy es solo texto: `titulo`, `texto`. La
operación real necesita adjuntar imágenes y video — la foto de portada
para el borrador de WordPress, el clip que va directo a Instagram/
Facebook. `docs/product/DOMAIN_MODEL.md` ya reservaba el nombre
`MediaAsset` desde Sprint 3A (`type`, `url_or_path`, `mime_type`,
`caption`) pero como *Value Object* conceptual, sin almacenamiento real
detrás.

Validado con el usuario antes de diseñar (mismo criterio que el resto de
Sprint 4A): el alcance son **imágenes y video** (no audio); el
almacenamiento es responsabilidad de Claude elegir; la política de
retención es **purgar una vez la solicitud queda completa**
(`fecha_cierre` ya no es `None`, ver ADR-006 Decisión 2), no
indefinidamente.

## Decisión 1 — `MediaAsset` es una entidad hija con su propio ciclo de vida, no un Value Object embebido

**Corrección respecto al diseño original (Sprint 3A):** `DOMAIN_MODEL.md`
lo describía como Value Object (`type`, `url_or_path`, `mime_type`,
`caption`), sin identidad propia. Diseñar la purga real revela que sí
necesita identidad: cada archivo tiene una clave de almacenamiento propia
que hay que poder borrar individualmente, un tamaño que hay que poder
sumar para no exceder límites, y una fecha de subida que la purga usa
para decidir qué borrar. Mismo caso que `DestinoPublicacion` en ADR-006
Decisión 1 — un value object no sostiene un ciclo de vida con acciones
externas (guardar el archivo, borrarlo). Pasa a ser una entidad hija por
`(solicitud, archivo)`, con su propia tabla y repositorio, igual patrón
que `DestinoPublicacion`.

| Atributo | Responsabilidad |
|---|---|
| `id` | Identidad propia — necesaria para pedir su borrado individual |
| `publication_request_id` | El padre; un `PublicationRequest` tiene 0..N `MediaAsset` |
| `tipo` | `MediaAssetType`: `IMAGEN`, `VIDEO` — audio deliberadamente fuera de alcance (no lo pidió el negocio) |
| `nombre_archivo` | Nombre original tal como lo subió el operador — para mostrarlo, nunca para construir la ruta de almacenamiento (evita path traversal) |
| `content_type` | MIME real detectado en la subida, no confiado del nombre de archivo |
| `tamano_bytes` | Para listar, mostrar, y para que la purga pueda reportar espacio liberado |
| `storage_key` | Clave opaca que el adaptador de almacenamiento usa internamente — el dominio nunca construye rutas de disco a mano |
| `fecha_subida` | Cuándo se adjuntó |
| `subido_por_user_id` | Quién lo adjuntó (auditoría, mismo criterio que `DestinoPublicacion.registrado_por_user_id`) |

No hay estados (`PENDIENTE`/`PUBLICADO`/...) — a diferencia de
`DestinoPublicacion`, un `MediaAsset` no tiene un flujo de confirmación;
existe desde que se sube hasta que se purga o se borra a mano. Su único
evento de ciclo de vida es la purga, resuelta con la misma disciplina
"timestamp de evento, no estado recalculado" que ya usa
`PublicationRequest.fecha_cierre` — ver Decisión 3.

## Decisión 2 — `MediaStorage`, un puerto nuevo; adaptador Railway Volume, no S3

Mismo patrón `Protocol` que `CMSPublisher` (ADR-006 Decisión 4): el
dominio y la API nunca saben *dónde* vive el archivo, solo hablan contra
un contrato.

```python
class MediaStorage(Protocol):
    def guardar(self, key: str, contenido: bytes) -> None: ...
    def leer(self, key: str) -> bytes: ...
    def eliminar(self, key: str) -> None: ...
```

**Adaptador elegido: disco local sobre un Railway Volume**
(`LocalDiskMediaStorage`), no un bucket S3/R2. Razones, mismo criterio
que ya justificó "WordPress primero, Application Password, no una
abstracción genérica de CMS" en ADR-006:

- Cero cuentas o credenciales nuevas para arrancar — Railway ya aloja
  este servicio; un Volume es un disco persistente que se monta al mismo
  servicio, sin depender de un tercero nuevo.
- La política de retención (Decisión 3: purgar a los pocos días de
  `fecha_cierre`) acota el tamaño acumulado — no es almacenamiento que
  crece sin límite, así que el argumento de escala de un object storage
  no aplica todavía.
- El puerto `MediaStorage` es la frontera: si el volumen de video crece
  más de lo que un Volume soporta cómodo, cambiar a un adaptador S3/R2
  es un adaptador nuevo detrás del mismo puerto, cero cambios en
  dominio/API/UI. No se cierra la puerta, se aplaza la decisión hasta
  que haga falta — mismo espíritu que ADR-006 Decisión 4 dejó abierto
  para automatizar Facebook/Instagram más adelante.

Los archivos **no se sirven como URL pública estática**: se descargan
vía un endpoint autenticado de la propia API (Decisión 4) — el Volume no
expone HTTP directo, y este es un panel interno con login, no un CDN
público.

Configuración nueva en `Settings` (mismo patrón que las variables
`wordpress_*`):

```python
media_storage_dir: Path = BASE_DIR / "database" / "media"  # producción: ruta del Volume
media_max_bytes_imagen: int = 10 * 1024 * 1024   # 10 MB
media_max_bytes_video: int = 200 * 1024 * 1024   # 200 MB
```

Los dos límites son un punto de partida razonable, no un número que el
negocio pidió — ajustables sin migración si resultan cortos o largos.

## Decisión 3 — Purga: N días después de `fecha_cierre`, por script explícito, no un hilo en segundo plano

Un `MediaAsset` se purga (se borra el archivo del storage y su fila)
`MEDIA_RETENTION_DIAS` días después de que su `PublicationRequest` queda
completa (`fecha_cierre` no es `None`). Mientras la solicitud sigue
abierta (`fecha_cierre is None`), sus adjuntos nunca se purgan sin
importar cuánto tiempo lleve pendiente.

```
purgable(media, solicitud) =
    solicitud.fecha_cierre is not None
    AND ahora >= solicitud.fecha_cierre + MEDIA_RETENTION_DIAS días
```

Valor por defecto: **7 días** (`media_retention_dias: int = 7` en
`Settings`) — igual que los límites de tamaño, un punto de partida
ajustable, no una cifra que el negocio fijó.

**Por qué un script, no un scheduler dentro del proceso FastAPI:** mismo
criterio ya establecido para `scripts/create_user.py` y
`scripts/migrate_historical_data.py` — una acción operativa explícita,
disparada por un humano o por un cron externo (Railway soporta
programar la ejecución de un servicio), no un hilo en segundo plano
compitiendo por recursos con la API. Menos moving parts en un sistema
que ya está en producción real; si en el futuro hace falta que corra
solo, se agenda el mismo script — el script no cambia.
`scripts/purgar_media_expirados.py`: recorre `MediaAsset`s purgables,
borra el archivo vía `MediaStorage.eliminar`, borra la fila, registra
cuánto espacio liberó. Idempotente — correrlo dos veces seguidas no
falla, la segunda vez simplemente no encuentra nada que purgar.

Un `MediaAsset` también se puede borrar a mano antes de la purga
automática (Decisión 4, `DELETE`) — por ejemplo, el operador subió el
archivo equivocado.

## Decisión 4 — Superficie HTTP: subir, listar, descargar, borrar — bajo `PublicationRequest`, no una colección aparte

Mismo lugar que `/publication-requests/{id}/destinos` en ADR-006 —
`MediaAsset` es siempre hijo de una solicitud, nunca se lista ni se
gestiona de forma independiente:

- `POST /publication-requests/{id}/media` — `multipart/form-data`, un
  archivo. Rechaza (422) si `content_type` no es imagen/video reconocido,
  o si excede `media_max_bytes_*`. Rechaza (409) si la solicitud ya está
  completa (`fecha_cierre` no es `None`) — no tiene sentido adjuntar
  material a algo que ya se publicó en todos sus destinos, y evita que
  algo suba justo antes de que la purga lo alcance.
- `GET /publication-requests/{id}/media` — metadata únicamente (sin el
  contenido binario) — mismo criterio que `GET .../destinos`.
- `GET /publication-requests/{id}/media/{media_id}/contenido` —
  streaming del archivo real, autenticado (requiere sesión, como el
  resto de la API) — así se previsualiza o se descarga para pegarlo a
  mano en Instagram/Facebook.
- `DELETE /publication-requests/{id}/media/{media_id}` — borrado manual
  antes de la purga automática.

**Deliberadamente fuera de alcance de este incremento** (igual espíritu
que ADR-006 Decisión 4 dejó Facebook/Instagram sin automatizar primero):

- Adjuntar automáticamente una imagen como *featured image* al crear el
  borrador de WordPress (`crear-borrador-wordpress`) — hoy ese borrador
  sigue siendo solo texto. Buen candidato a incremento futuro, no bloquea
  nada de lo de aquí.
- Redimensionar/generar miniaturas — se sirve el archivo tal cual se
  subió.
- Límite de cantidad de adjuntos por solicitud — no lo pidió el negocio;
  se revisita si en la práctica alguien sube demasiados.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| S3 / Cloudflare R2 desde el arranque | Cuenta y credenciales nuevas antes de tener evidencia de que un Volume no alcanza; la purga ya acota el tamaño acumulado |
| Servir el archivo como URL pública directa (sin pasar por la API) | Un Volume de Railway no expone HTTP propio; y este panel es interno con login, no hace falta una URL pública |
| Purgar por límite de tamaño total en vez de por antigüedad | No resuelve el caso real: una solicitud completa hace tiempo no necesita conservar su adjunto, sin importar cuánto espacio total se esté usando |
| Scheduler en segundo plano dentro del proceso FastAPI | Más moving parts en producción real; un script explícito (mismo patrón que `create_user.py`/`migrate_historical_data.py`) es más simple de operar y de razonar |
| `MediaAsset` como Value Object embebido (diseño original Sprint 3A) | No sostiene un ciclo de vida con acciones externas (borrar el archivo real) sin una identidad propia — mismo argumento que ya resolvió `DestinoPublicacion` en ADR-006 |

## Consecuencias

- `docs/product/DOMAIN_MODEL.md`: la sección `MediaAsset` se corrige de
  Value Object a entidad hija (mismo tratamiento que `DestinoPublicacion`
  recibió de ADR-006), con su forma real.
- Nuevo puerto `core/ports/media_storage.py` (`MediaStorage`) y su
  adaptador `agents/storage/local_disk.py` (`LocalDiskMediaStorage`) —
  mismo layout que `agents/wordpress/`.
- Nueva tabla `media_assets` (migración Alembic aditiva, mismo patrón que
  `destinos_publicacion`).
- `Settings` gana `media_storage_dir`, `media_max_bytes_imagen`,
  `media_max_bytes_video`, `media_retention_dias`.
- Nuevo script `scripts/purgar_media_expirados.py`.
- Ningún cambio a `DestinoPublicacion`, `esta_completa`, o el consumo de
  cuota — `MediaAsset` es puramente aditivo sobre lo que ADR-006 ya
  construyó, cierra el rollout de Sprint 4A.
