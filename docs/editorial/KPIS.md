# KPIs de la plataforma

> Se definen ahora, antes de implementarse (planeado para el sprint
> "Analytics" y v1.4 — ver [docs/ROADMAP.md](../ROADMAP.md)), para que la
> instrumentación necesaria (marcas de tiempo, motivos de rechazo) se
> capture desde el primer sprint que la genera, en vez de tener que
> reconstruirse después.

## Los KPIs

### Tiempo de detección (Detection Time)

**Qué mide:** tiempo entre que la fuente publicó algo y Discovery Engine
lo detectó (`NewsCandidate.discovered_at - NewsCandidate.published_at`,
ambos campos ya implementados).

**Por qué importa:** acota, con un número real, qué tan "última hora"
puede ser realmente la plataforma — ver
[FRESHNESS_MODEL.md](FRESHNESS_MODEL.md). Un Detection Time alto en una
fuente específica es una señal de que esa fuente necesita revisarse
(¿su feed se actualiza con retraso? ¿la cadencia de escaneo es
insuficiente?).

### Tiempo de aprobación (Approval Time)

**Qué mide:** tiempo entre que se notifica un candidato a un editor y su
decisión (aprobar/rechazar/pedir cambios) — ligado a
`EditorialTask` (ya implementada).

**Por qué importa:** es la medida más directa de si la plataforma está
cumpliendo su propósito. Ver
[docs/product/PRODUCT_VISION.md](../product/PRODUCT_VISION.md): el
producto existe para ahorrar tiempo editorial, y este KPI es la prueba
(o refutación) de que lo está logrando.

### Tiempo de publicación (Publication Time)

**Qué mide:** tiempo entre la aprobación editorial y la publicación
manual efectiva en WordPress.

**Por qué importa:** un tiempo alto aquí, a diferencia del Approval Time,
no es un problema de la plataforma — es friction operativa del editor
(¿tiene que hacer pasos manuales adicionales en WordPress?). Separar este
KPI del anterior evita atribuirle a la IA una demora que es, en realidad,
del proceso de publicación humano.

### Noticias rechazadas (Rejected News)

**Qué mide:** cantidad y proporción de candidatos que un editor rechaza,
con su motivo (ver [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-10).

**Por qué importa:** una tasa de rechazo alta y sostenida es la señal más
directa de que Editorial Score o Confidence están mal calibrados para
esta fuente o este cliente — es una métrica de calidad del sistema, no
solo del contenido.

### Tasa de duplicados (Duplicate Rate)

**Qué mide:** proporción de candidatos detectados que resultan ser
duplicados de algo ya procesado (ver
[EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-05).

**Por qué importa:** una tasa alta y sostenida en una fuente específica
sugiere que esa fuente se solapa mucho con otras ya configuradas — señal
para revisar la lista de fuentes, no solo el motor de deduplicación.

### Artículos publicados (Articles Published)

**Qué mide:** conteo de `Article` que llegaron a `PUBLISHED`, en el
tiempo.

**Por qué importa:** volumen de producción real — el denominador contra
el que se leen todos los demás KPIs (por ejemplo, "tiempo de aprobación
promedio sobre cuántos artículos").

### Publicaciones en redes generadas (Social Posts Generated)

**Qué mide:** cantidad de propuestas de contenido para redes que el
futuro agente Social genera, y cuántas de ellas se aprueban vs. se
descartan.

**Por qué importa:** mide la utilidad real de esa capacidad — si la
mayoría de las propuestas se descartan sin usar, es una señal de que el
agente Social necesita ajuste antes de considerarse confiable.

### Productividad del editor (Editor Productivity)

**Qué mide:** artículos procesados (aprobados, rechazados o con cambios
pedidos) por editor, por unidad de tiempo.

**Por qué importa:** es la métrica más cercana al valor de negocio
prometido en [docs/VISION.md](../VISION.md) — "ahorrar tiempo, no
reemplazar juicio". Un aumento sostenido en este número, sin que la
calidad editorial baje (ver Rejected News como contrapeso), es la
evidencia de que el producto funciona.

## Cómo se relacionan entre sí

Ningún KPI se lee de forma aislada. Un Approval Time bajo con una tasa de
rechazo alta no es éxito — es un editor aprobando rápido sin revisar bien
(ver [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md): la velocidad nunca
debe venir a costa del criterio). Estos KPIs se diseñan para leerse en
conjunto, no en aislamiento — el futuro agente Analytics (Fase 7 /
"Analytics" en [docs/ROADMAP.md](../ROADMAP.md)) es responsable de
presentarlos así.

## Estado de implementación

Ninguno de estos KPIs está instrumentado hoy. Los campos de los que
dependen (`NewsCandidate.discovered_at`/`published_at`,
`EditorialTask.created_at`, `Article.created_at`) sí existen en código —
lo que falta es el agregador que los convierta en métricas, planeado para
el sprint "Analytics".
