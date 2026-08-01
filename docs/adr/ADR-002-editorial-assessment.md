# ADR-002: EditorialAssessment como Value Object, y separación de Publication

- **Estado:** Aceptado
- **Fecha:** 2026-07-09 (Sprint 2.3.1 — Domain Refinement)
- **Contexto del documento:** ver
  [ADR-001](ADR-001-project-vision.md) para las convenciones de formato.
  Este ADR no reemplaza ni modifica ADR-001 — lo extiende con dos
  decisiones de modelado de dominio tomadas durante la revisión
  arquitectónica del Sprint 2.3 (especificación editorial), antes de que
  Sprint 3 empiece a implementar código sobre estos conceptos.

## Contexto

Sprint 2.3 introdujo Editorial Score, Confidence y Freshness como tres
señales que priorizan (nunca deciden) qué le llega primero a un editor —
ver [docs/editorial/CONFIDENCE_MODEL.md](../editorial/CONFIDENCE_MODEL.md).
Al documentarlas, quedó una pregunta implícita sin resolver: ¿a qué
entidad pertenecen estos valores? La opción más obvia — agregarlos como
campos de `NewsCandidate` o de `Article` — se descartó explícitamente
durante la revisión, por las razones de este ADR.

Al mismo tiempo,
[docs/editorial/NEWS_LIFECYCLE.md](../editorial/NEWS_LIFECYCLE.md)
(también Sprint 2.3) dejó una discrepancia señalada explícitamente como
pregunta abierta: los estados `Shared` y `Archived` no tenían equivalente
en `ArticleStatus` (`core/entities/article.py`, Sprint 2). Este ADR
también resuelve esa pregunta.

## Decisión 1 — Editorial Score, Confidence y Freshness viven en un Value Object nuevo: `EditorialAssessment`

**No** se agregan como campos de `NewsCandidate` ni de `Article`. Se
introduce `EditorialAssessment`, con los atributos:

| Atributo | Responsabilidad |
|---|---|
| `score` | El valor de Editorial Score en el momento del cálculo — ver [docs/editorial/EDITORIAL_SCORE.md](../editorial/EDITORIAL_SCORE.md) |
| `confidence` | El valor de Confidence en el momento del cálculo — ver [docs/editorial/CONFIDENCE_MODEL.md](../editorial/CONFIDENCE_MODEL.md) |
| `freshness` | El valor de Freshness en el momento del cálculo — ver [docs/editorial/FRESHNESS_MODEL.md](../editorial/FRESHNESS_MODEL.md) |
| `priority` | La prioridad combinada resultante — el número/orden que realmente usa la bandeja de un editor, derivado de los tres anteriores más cualquier ajuste manual |
| `reasoning` | Explicación legible por humanos de por qué se llegó a estos valores — lo que hace que la asistencia sea auditable, no una caja negra |
| `calculated_at` | Cuándo se calculó esta evaluación específica |

### Por qué es un Value Object, no una entidad

Un Value Object en DDD no tiene identidad propia — se define enteramente
por sus valores, y cuando algo sobre él cambia, se reemplaza por una
instancia nueva, no se muta. Eso es exactamente lo que necesita una
evaluación editorial: si un rumor se confirma y su Confidence sube, eso
no es "actualizar" la evaluación anterior — es una evaluación distinta,
en un momento distinto, potencialmente con un `reasoning` distinto. La
evaluación anterior sigue siendo un hecho histórico válido ("en ese
momento, con esa información, esto es lo que sabíamos").

Esto no introduce un patrón nuevo en el proyecto: todas las entidades en
`core/entities/` (Sprint 2) ya son `frozen=True` — inmutables por
diseño. `EditorialAssessment` aplica la misma disciplina a un concepto
que, además, necesita poder repetirse en el tiempo para el mismo
candidato.

### Por qué puede recalcularse varias veces

Un `NewsCandidate` puede tener **varias** `EditorialAssessment` a lo
largo de su vida — cada recálculo es una nueva instancia, nunca una
edición de la anterior. Esto habilita, sin ningún cambio adicional de
diseño:

- Un historial auditable de cómo cambió el juicio de la plataforma sobre
  un candidato (útil para [KPIS.md](../editorial/KPIS.md) y para
  entender por qué algo se notificó con cierta urgencia).
- Probar distintos algoritmos de cálculo en paralelo (ver "Evolución
  futura" abajo) sin perder ninguna evaluación anterior.

### Por qué se separa de `NewsCandidate` y de `Article`

- **Separación de responsabilidades.** `NewsCandidate` y `Article`
  describen **qué es** el contenido — hechos relativamente estables.
  `EditorialAssessment` describe **qué opina la plataforma de él ahora
  mismo** — un juicio que cambia. Mezclar ambos en la misma entidad
  obligaría a mutar un registro que, por lo demás, se diseñó inmutable
  (ver arriba), o a perder el historial de evaluaciones anteriores.
- **El momento del cálculo no coincide con el ciclo de vida de
  `Article`.** La primera evaluación ocurre sobre un `NewsCandidate`,
  antes de que exista ningún `Article` — ver
  [docs/editorial/NEWS_LIFECYCLE.md](../editorial/NEWS_LIFECYCLE.md),
  estado `Scored`. Si `EditorialAssessment` fuera parte de `Article`, no
  habría dónde guardarla en ese punto del flujo.
- **Testabilidad.** Un Value Object independiente se puede construir,
  comparar y probar sin necesitar un `NewsCandidate` ni un `Article`
  completos — consistente con
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 5.

### Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Agregar `score`/`confidence`/`freshness` como campos sueltos de `NewsCandidate` | Obligaría a mutar una entidad diseñada inmutable cada vez que se recalcula, o a perder el historial de evaluaciones anteriores |
| Agregar los mismos campos a `Article` | `Article` no existe todavía en el punto del flujo donde ocurre la primera evaluación |
| Un solo campo `priority: float` sin desglosar Score/Confidence/Freshness por separado | Pierde la distinción explícita que [CONFIDENCE_MODEL.md](../editorial/CONFIDENCE_MODEL.md) establece como valiosa — un editor necesita saber *por qué* algo tiene prioridad alta, no solo que la tiene |

### Evolución futura

- Distintos algoritmos o versiones de cálculo podrían producir
  `EditorialAssessment` etiquetadas con una versión, permitiendo comparar
  enfoques sin afectar el candidato evaluado.
- Podría coexistir una evaluación automática con un ajuste manual de un
  Editor Jefe (ver
  [docs/editorial/EDITOR_PERSONAS.md](../editorial/EDITOR_PERSONAS.md)),
  cada una como su propia `EditorialAssessment`, con `reasoning`
  distinguiendo el origen.
- En la plataforma multi-cliente (ver
  [docs/product/SAAS_EVOLUTION.md](../product/SAAS_EVOLUTION.md)), los
  pesos que alimentan `score` podrían variar por `MediaOutlet` sin
  cambiar la forma del Value Object, solo el cálculo que lo produce.

## Decisión 2 — `Publication` se separa de `Article`

**Un `Article` representa contenido editorial. Una `Publication`
representa la distribución de ese contenido en un canal.** Un mismo
`Article` puede generar muchas `Publication` — WordPress, Facebook,
Instagram, Telegram (como canal público, distinto del
`NotificationChannel` interno del equipo editorial), X, TikTok, o
cualquier canal futuro — cada una con su propio `PublicationStatus`
(`Pending`, `Scheduled`, `Published`, `Failed`, `Archived`, `Cancelled`).

Ver [docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md), sección
"Publication", para las responsabilidades completas, y
[docs/editorial/NEWS_LIFECYCLE.md](../editorial/NEWS_LIFECYCLE.md) para
el diagrama de estados.

### Por qué `Publication` es su propia entidad

- **La relación es uno a muchos, no uno a uno.** Un solo campo de estado
  en `Article` no puede representar "publicado en WordPress, programado
  en Facebook, cancelado en Instagram" simultáneamente.
- **Cada canal tiene su propio ciclo de vida, independiente de los
  demás.** Que Instagram falle no debería afectar el estado de
  WordPress, ni viceversa.
- **Auditoría por canal.** Cada `Publication` necesita su propio rastro
  (cuándo, quién aprobó esa distribución específica, el identificador o
  URL en ese canal) — mezclar esto en `Article` lo haría cada vez más
  complejo a medida que se agregan canales.

### Por qué `ArticleStatus` se mantiene simple

`ArticleStatus` (`DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`,
`PUBLISHED` — ya implementado, Sprint 2, sin cambios de código en este
ADR) describe únicamente el estado **editorial** del contenido: ¿está
listo? ¿fue aprobado? Nunca describe distribución. Si `ArticleStatus`
intentara capturar también el estado de cada canal, terminaría
necesitando combinaciones como "publicado en WordPress pero pendiente en
Instagram" — un enum no es la herramienta correcta para eso; una entidad
relacionada (`Publication`) sí.

Esto resuelve la pregunta que
[docs/editorial/NEWS_LIFECYCLE.md](../editorial/NEWS_LIFECYCLE.md) había
dejado abierta explícitamente: `Shared` y `Archived` no se agregan a
`ArticleStatus` — pertenecen a `PublicationStatus`.

### Beneficios

- `ArticleStatus` no necesita crecer cada vez que se agrega un canal de
  distribución nuevo (ver
  [docs/ROADMAP.md](../ROADMAP.md), sprint "Social" en adelante).
- El agente Social (futuro) puede operar sobre `Publication` sin tocar
  `Article` ni su estado.
- Analytics (ver [docs/editorial/KPIS.md](../editorial/KPIS.md)) puede
  medir "publicaciones en redes generadas" y su tasa de éxito por canal
  sin ambigüedad.

### Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Un campo `published_channels: list[str]` en `Article` | No captura el estado independiente de cada canal, solo si "tocó" ese canal en algún momento |
| Extender `ArticleStatus` con valores como `PUBLISHED_WORDPRESS`, `PUBLISHED_SOCIAL` | Combinatoria explosiva en cuanto se agrega un tercer o cuarto canal; no permite estados simultáneos distintos por canal |

## Consecuencias

- `docs/product/DOMAIN_MODEL.md`, `docs/editorial/NEWS_LIFECYCLE.md`,
  `docs/editorial/EDITORIAL_SCORE.md`,
  `docs/editorial/CONFIDENCE_MODEL.md` y
  `docs/editorial/HUMAN_IN_THE_LOOP.md` se actualizaron para reflejar
  estas dos decisiones (ver el reporte de Sprint 2.3.1).
- Ningún código existente cambia — `NewsCandidate`, `Article` y
  `ArticleStatus` (Sprint 2) quedan exactamente como están. Estas
  decisiones afectan cómo se implementará Sprint 3 en adelante, no lo ya
  construido.
- Queda una pregunta de diseño de datos explícitamente sin resolver: la
  relación exacta entre el campo `NewsCandidate.confidence` (ya en
  código) y `EditorialAssessment.confidence` (conceptual) — ver
  [docs/editorial/CONFIDENCE_MODEL.md](../editorial/CONFIDENCE_MODEL.md).
  Se resuelve al implementar, no aquí.
