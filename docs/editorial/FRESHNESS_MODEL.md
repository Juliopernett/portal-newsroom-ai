# Modelo de Freshness

> Antes de leer este documento, ver
> [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md), sección "Cómo interactúan
> Score, Confidence y Freshness" para la comparación completa entre los
> tres ejes.

## Qué mide

Freshness responde: **¿qué tan reciente y sensible al tiempo es este
contenido?** No mide importancia (eso es
[Editorial Score](EDITORIAL_SCORE.md)) ni certeza (eso es
[Confidence](CONFIDENCE_MODEL.md)) — mide una sola cosa, el tiempo, y
cómo ese tiempo cambia la urgencia con la que algo necesita atención
humana.

**Estado:** conceptual. No implementado todavía, pero se apoya en campos
que sí existen hoy: `NewsCandidate.published_at` (cuándo lo publicó la
fuente, si lo informa) y `NewsCandidate.discovered_at` (cuándo lo
detectó Discovery Engine) — ver
`core/entities/news_candidate.py` y
[docs/architecture/discovery-engine.md](../architecture/discovery-engine.md).

## Cómo se calcularía

A partir de `published_at` cuando la fuente lo provee (mide la
antigüedad real del hecho); si no está disponible, a partir de
`discovered_at` como aproximación (mide desde cuándo la plataforma lo
sabe, que es lo mejor que se puede hacer sin una fecha de publicación
confiable).

## Categorías

| Categoría | Ventana ilustrativa | Qué significa |
|---|---|---|
| Última hora (Breaking News) | Minutos desde publicado | El hecho está ocurriendo o acaba de ocurrir; alta sensibilidad al tiempo |
| Noticia reciente (Recent News) | Horas desde publicado | Todavía plenamente relevante, sin la urgencia de última hora |
| Noticia vieja (Old News) | Días desde publicado | La ventana de relevancia inmediata pasó; puede seguir siendo válida pero ya no es prioritaria por tiempo |
| Contenido evergreen | Sin ventana de tiempo | No decae — un explicativo cultural, un perfil, la historia de una tradición. Freshness no le resta valor, simplemente no aplica urgencia |

Los umbrales exactos (minutos/horas/días) son ilustrativos — se calibran
cuando esto se implemente, según la cadencia real de las fuentes de
Portal Vallenato.

## Diferencia con "noticia vieja" como penalización de Score

Freshness es una medición continua de tiempo. La "penalización por
noticia vieja" en [EDITORIAL_SCORE.md](EDITORIAL_SCORE.md) es el efecto
que una Freshness baja tiene sobre el Score — están relacionadas pero no
son lo mismo: Freshness es el dato, la penalización de Score es una de
las consecuencias de ese dato.

## Cómo afecta las notificaciones

| Freshness | Efecto en la notificación al editor |
|---|---|
| Última hora | Notificación individual e inmediata, marcada como urgente |
| Reciente | Notificación normal, en el flujo habitual |
| Vieja | Prioridad baja — candidata a agruparse en un resumen en vez de notificar individualmente |
| Evergreen | Sin urgencia por tiempo — se podría presentar como "contenido disponible" en vez de "algo que revisar ahora" |

## Ejemplos

- Un comunicado del Festival Vallenato detectado 8 minutos después de
  publicado → **Última hora**. Si además tiene Score y Confidence altos,
  ver el caso "ideal" en
  [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md).
- La misma nota, si por algún motivo Discovery Engine la detecta recién
  4 días después (por ejemplo, una fuente que tardó en indexarla) →
  **Vieja**, aunque el contenido siga siendo relevante — se notifica con
  baja urgencia, no se descarta (ver
  [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-10).
- Un artículo sobre el origen histórico del vallenato silvestre →
  **Evergreen** — no compite por atención urgente, pero tampoco pierde
  valor con el tiempo.

## Ver también

- [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md) — comparación completa entre
  Score, Confidence y Freshness.
- [EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md) — dónde
  encaja el cálculo de Freshness en el flujo completo.
