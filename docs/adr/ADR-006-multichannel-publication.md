# ADR-006: PublicationRequest evoluciona a contenido multicanal — DestinoPublicacion y cierre por completitud

- **Estado:** Aceptado
- **Fecha:** 2026-08-05 (Sprint 4A — Reestructuración de Solicitudes de
  Publicación)
- **Contexto del documento:** ver [ADR-001](ADR-001-project-vision.md)
  para las convenciones de formato. Extiende [ADR-002](ADR-002-editorial-assessment.md)
  (el precedente `Article`/`Publication`) y [ADR-004](ADR-004-commercial-manager.md)
  (Commercial Manager), no los reemplaza. Corrige, solo para
  `PublicationRequest`/`MediaAsset`, la divergencia documental que
  `CHANGELOG.md` (sección `[Unreleased]`, nota "Domain Adjustment /
  divergencia Sprint 3B") ya dejó registrada como pendiente — el resto de
  esa divergencia (`CommercialContact`, `Contract`, `Plan`, `Campaign`,
  `Alert`, "Publication Inbox" como bounded context multicanal) sigue sin
  reconciliarse y queda fuera de este ADR.

## Contexto

Portal Vallenato opera hoy `PublicationRequest` como una entidad plana
(`pauta_id`, `texto`, `estado`, `prioridad_manual`, `observaciones`) que
asume una sola publicación, en un solo canal implícito, sin título ni
multimedia. La operación real necesita distribuir un mismo contenido a
varios destinos — WordPress (automatizable vía REST API), Facebook e
Instagram (registro manual de enlace) — y dejar la puerta abierta a más
canales (TikTok, YouTube, X, Threads) sin rediseñar el modelo cada vez.

Además, la cuota de una `Pauta` debe consumirse **una sola vez** por
solicitud comercial, sin importar cuántos destinos tenga, y solo cuando
esa publicación quede completa en todos los destinos elegidos — no
cuando un canal específico (ej. WordPress) publique.

El flujo funcional completo (desde que llega el material hasta el
reporte final de campaña) se validó primero con el usuario antes de
tomar estas decisiones; este ADR documenta el resultado de esa
validación, no un diseño especulativo previo al negocio real (mismo
criterio que ya aplicó Domain Discovery en Sprint 3B).

## Decisión 1 — `DestinoPublicacion`, una entidad hija por `(solicitud, canal)`

Se introduce `DestinoPublicacion`: un registro por combinación de
`PublicationRequest` y canal, con su propio ciclo de vida
(`PENDIENTE` → `PUBLICADO` \| `FALLIDO` \| `CANCELADO`). Un mismo
`PublicationRequest` genera **varios** `DestinoPublicacion` — el mismo
rol que `Publication`/`PublicationStatus` ya cumplen para `Article` en
`docs/product/DOMAIN_MODEL.md` (ver [ADR-002](ADR-002-editorial-assessment.md)),
aplicado ahora al pilar comercial en lugar del editorial. No se fusiona
con la entidad ya existente `Publication` (todavía conceptual, sin
construir) porque [ADR-003](ADR-003-publication-inbox.md) ya estableció
que el contenido orgánico y el comercial nunca convergen en una entidad
compartida — `DestinoPublicacion` es el equivalente comercial, no el
mismo objeto.

| Atributo | Responsabilidad |
|---|---|
| `canal` | `CanalPublicacion`: `WORDPRESS`, `FACEBOOK`, `INSTAGRAM` — agregar un canal futuro no cambia esta forma |
| `estado` | `PENDIENTE`, `PUBLICADO`, `FALLIDO`, `CANCELADO` |
| `wp_post_id` / `wp_url` | Solo si `canal=WORDPRESS`, llenados por `CMSPublisher.create_draft` |
| `url_publicacion` | Solo si `canal` es Facebook/Instagram — enlace pegado a mano |
| `registrado_por_user_id` | Quién confirmó la publicación o registró el enlace |
| `fecha_publicacion` | Cuándo quedó realmente publicado ese destino |
| `ultimo_error` | Motivo si `FALLIDO` |

Un destino `FALLIDO` es cancelable a mano — no debe existir un estado
del que no haya salida, porque eso bloquearía indefinidamente el cierre
de la solicitud completa (ver Decisión 2).

## Decisión 2 — `estado` de `PublicationRequest` vuelve a ser solo triage; "completa" es derivada, salvo su fecha

Hasta ahora, `PUBLICADA` era el estado terminal que representaba "ya se
publicó". Eso deja de sostenerse en cuanto una solicitud puede tener
varios destinos con estados independientes. `PublicationRequestStatus`
se reduce a describir únicamente el triage de intake: `RECIBIDA`,
`ACEPTADA`, `CANCELADA` — el mismo rol, deliberadamente simple, que
`ArticleStatus` cumple para `Article` (ver ADR-002); la complejidad de
"qué tan publicado está" vive enteramente en `DestinoPublicacion`, no
aquí.

Se define una condición derivada, **nunca almacenada como campo**
(misma disciplina que ya usa `PautaService.publicaciones_consumidas`,
`Pauta.peso_comercial` y `Pauta.tipo` — computar en vez de guardar un
valor que puede desincronizarse):

```
esta_completa(solicitud, destinos) =
    destinos no está vacío
    AND todos los destinos están en estado terminal (PUBLICADO o CANCELADO)
    AND al menos uno terminó en PUBLICADO
```

**Excepción deliberada — `fecha_cierre` sí se almacena.** Es un
timestamp de auditoría, asignado por el sistema una sola vez, en el
momento exacto en que `esta_completa` pasa a `True` — nunca editable a
mano, nunca recalculado. Mismo patrón que `Pauta.fecha_registro`
(agregado 2026-08-05 tras un incidente real donde no había forma
confiable de encontrar "la solicitud que se acaba de cerrar"): un valor
derivado explica *qué es cierto ahora*, pero no *cuándo pasó* — para
eso se necesita un timestamp fijado en el instante del evento, no
recalculado en cada lectura.

## Decisión 3 — La cuota de una `Pauta` se consume por solicitud completa, no por canal

`PautaService.publicaciones_consumidas` cambia su filtro de
`solicitud.estado == PUBLICADA` a `esta_completa(solicitud, destinos)`.
La cuota se consume **una sola vez por solicitud**, sin importar cuántos
destinos tuvo ni cuáles — específicamente, **no** se ata a que el
destino WordPress en particular esté publicado (alternativa
descartada, ver más abajo).

Este es el cambio de mayor riesgo de negocio del ADR — ya hubo un
incidente real de cuota el 2026-08-05 (ver `CHANGELOG.md`/memoria de
proyecto: la cuota se calculaba sumada entre pautas cuando debía ser
por contrato individual). Antes de desplegar este paso (Incremento 4)
se valida el nuevo cálculo contra las pautas y solicitudes reales ya en
producción, para confirmar que ningún cliente cambia de número.

## Decisión 4 — WordPress es el primer canal automatizado; el resto queda con una estrategia por canal, no un `if/else`

Se reutiliza `core.ports.cms_publisher.CMSPublisher` (`create_draft`,
sin `publish()`). "Automático" significa exclusivamente que el sistema
crea el borrador en WordPress — poner el post en vivo sigue siendo una
acción humana explícita, por lo que esto **no viola**
[docs/PROJECT_RULES.md](../PROJECT_RULES.md) regla 1 ("el sistema nunca
publica automáticamente"). Facebook e Instagram no tienen puerto de
automatización todavía — solo registro manual de enlace — pero
`DestinoPublicacion` ya deja espacio para agregar una estrategia de
automatización por canal más adelante (un puerto nuevo por canal, igual
que `CMSPublisher` hoy) sin cambiar la forma de la entidad.

**Corrección tras implementar (Incremento 3):** este ADR decía que
`CMSPublisher` se reutilizaría "sin modificarlo". Construir el adaptador
real reveló que `create_draft` necesitaba devolver tanto el `post_id`
como el `url` del borrador — un `str` opaco no podía cargar los dos, y
`DestinoPublicacion` necesita ambos (`wp_post_id` para futuras consultas
de estado contra WordPress, `wp_url` para reportes y enlaces al
cliente). Se agregó `CMSDraftResult` (`NamedTuple` de `post_id` + `url`)
como tipo de retorno. Sin riesgo real: ningún adaptador existía todavía
cuando se hizo el cambio. El adaptador real vive en
`agents/wordpress/client.py` (`WordPressCMSPublisher`), autenticado con
un Application Password de WordPress (nunca la contraseña de inicio de
sesión de la cuenta) vía HTTP Basic Auth contra
`/wp-json/wp/v2/posts`, siempre con `status=draft`.

## Decisión 5 — Rollout incremental; cada incremento deja el sistema desplegable

Portal Newsroom AI está en producción real (Railway), alimentado a
diario. Ningún incremento puede dejar el sistema en un estado no
desplegable. Orden acordado con el usuario:

1. Modelo de dominio (`DestinoPublicacion`, `titulo`, `fecha_cierre`) —
   puramente aditivo, el flujo actual de "Publicar" sigue funcionando sin
   cambios visibles. **Corrección tras implementar (2026-08-05):**
   `PublicationRequestStatus` **no** se reduce en este incremento —
   `PUBLICADA` se mantiene. Retirarla ahora habría exigido reescribir
   `PautaService.publicaciones_consumidas` y, en cascada,
   `AnalyticsService`, `decision_engine` y las rutas de dashboard/
   insights (30 archivos referencian estos conceptos) sin la validación
   contra datos reales que la Decisión 3 exige antes de ese cambio — ese
   cutover queda confirmado para el Incremento 4, junto con el consumo de
   cuota por completitud, no aquí. Ver `CHANGELOG.md`, sección
   `[Unreleased]`, entrada "Sprint 4A, Incremento 1".
2. Nuevo formulario de solicitudes (agrega `titulo`; tipo de contenido
   queda fuera de alcance).
3. Integración con WordPress: creación automática de borradores.
4. Registro de Facebook/Instagram + consumo de cuota por completitud +
   el cutover de `PublicationRequestStatus` diferido del Incremento 1
   (validado contra datos reales antes de desplegarse, ver Decisión 3).
5. Reportes automáticos para clientes (generación automática, envío
   sigue siendo manual — no hay integración de envío en este sprint).
6. Gestión de multimedia y almacenamiento temporal — deliberadamente al
   final; introduce una dependencia externa nueva (storage) que no
   bloquea nada de lo anterior. Su diseño detallado (proveedor,
   retención, reglas de purga) queda para cuando se llegue a ese
   incremento, no se fija en este ADR.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Un solo `DestinoPublicacion` con columnas por canal en vez de una fila por canal | No escala a canales futuros sin agregar columnas cada vez; una fila por canal es la misma forma sin importar cuántos se agreguen |
| Fusionar `DestinoPublicacion` con la `Publication` conceptual de `Article` | ADR-003 ya estableció que orgánico y comercial nunca convergen en una entidad compartida |
| Cuota consumida cuando el destino WordPress específico se publica | No sostiene el caso de una solicitud sin WordPress (solo redes) ni refleja "la publicación comercial completa", que es lo que el negocio realmente factura |
| `esta_completa` como campo `estado` adicional (ej. `COMPLETADA`) en vez de condición derivada | Reintroduce el mismo problema que la cuota ya resolvió: un valor que puede desincronizarse de los destinos reales — la única excepción aceptada es `fecha_cierre`, un timestamp de evento, no un estado recalculable |
| Cierre por confirmación humana explícita en vez de automático | El usuario prefirió detección automática apenas el último destino pendiente cambia de estado — sin paso manual adicional |

## Consecuencias

- `docs/product/DOMAIN_MODEL.md` se actualiza: sección `PublicationRequest`
  corregida a su forma real (no la de ADR-003) más los campos de Sprint
  4A, y nueva sección `DestinoPublicacion`. El resto de la divergencia de
  Sprint 3B (`CommercialContact`, `Contract`, `Plan`, `Campaign`, `Alert`)
  **no** se toca aquí.
- `PautaService.publicaciones_consumidas` cambia de criterio (Decisión 3)
  — requiere validación contra datos reales antes del Incremento 4.
- `core.services.publication_request_service.mark_as_published` deja de
  tener sentido tal cual (¿publicado en cuál destino?) — se reemplaza por
  operaciones sobre `DestinoPublicacion` en el Incremento 1.
- Multimedia (`MediaAsset`, storage temporal, purga) queda fuera de
  alcance de este ADR — se diseña en su propio momento, Incremento 6.
- Ningún canal nuevo (TikTok, YouTube, X, Threads) se implementa ahora —
  la forma de `DestinoPublicacion` ya los admite sin cambios futuros.
