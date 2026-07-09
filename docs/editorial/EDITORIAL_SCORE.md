# Editorial Score

> Antes de leer este documento, ver
> [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md), sección "Cómo interactúan
> Score, Confidence y Freshness" — Editorial Score es uno de tres ejes
> relacionados pero distintos, y esa tabla comparativa es el punto de
> referencia completo.

## Qué mide

Editorial Score mide **qué tan importante sería esta noticia para el
medio, asumiendo que es cierta** — independientemente de qué tan seguros
estemos de que lo es (eso es [Confidence](CONFIDENCE_MODEL.md)) y de qué
tan reciente sea (eso es [Freshness](FRESHNESS_MODEL.md)).

**Dónde vive (Sprint 2.3.1):** Editorial Score **no** es un campo de
`NewsCandidate` ni de `Article` — es uno de los atributos de
`EditorialAssessment`, un Value Object separado que representa la
evaluación editorial de un candidato en un momento dado, y que puede
recalcularse más de una vez. Ver
[docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md), sección
"EditorialAssessment", y
[docs/adr/ADR-002-editorial-assessment.md](../adr/ADR-002-editorial-assessment.md)
para el razonamiento completo de por qué se modela así.

## Por qué existe

Un equipo editorial pequeño no puede revisar cada candidato detectado con
la misma atención. Editorial Score no decide qué se publica — decide qué
le llega primero a un editor y con cuánta prioridad, para que su tiempo
limitado se use en lo que más importa. Es un mecanismo de **priorización
de la atención humana**, no de selección de contenido — ver
[HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).

**Estado:** conceptual. No implementado en código todavía — planeado
para el sprint "AI scoring engine" (v1.3), ver
[docs/ROADMAP.md](../ROADMAP.md). Este documento define su forma para
que, cuando se implemente, no haya que rediseñarla desde cero.

## Factores posibles

### Factores que aumentan el Score

| Factor | Por qué aumenta el Score |
|---|---|
| Artista en tendencia | Mayor interés de la audiencia actual |
| Anuncio oficial | Fuente primaria, alto valor informativo |
| Exclusiva | El medio sería el primero o uno de los pocos en cubrirlo |
| Última hora (Breaking News) | Alto valor por su urgencia — ver también [FRESHNESS_MODEL.md](FRESHNESS_MODEL.md), con el que este factor se relaciona pero no se confunde: aquí importa que **sea** urgente por naturaleza, no cuánto tiempo pasó desde que se detectó |
| Relacionado con el Festival Vallenato | Relevancia editorial directa para la identidad del medio |
| Alto engagement (señales sociales) | Evidencia de que la audiencia ya está interesada |

### Factores que penalizan el Score

| Factor | Por qué penaliza |
|---|---|
| Penalización por duplicado | Un candidato que reitera algo ya cubierto aporta poco valor adicional — ver [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-05 |
| Penalización por noticia vieja | Contenido cuya ventana de relevancia ya pasó pierde valor editorial, salvo que sea evergreen — ver [FRESHNESS_MODEL.md](FRESHNESS_MODEL.md) |

## No confundir con `Source.priority`

`Source.priority` (implementado, `core/entities/source.py`) es una
preferencia fija por fuente, configurada una vez ("esta fuente
generalmente aporta contenido más relevante que aquella"). Editorial
Score es una señal dinámica calculada por candidato individual, en cada
detección — dos candidatos de la misma fuente pueden tener Scores muy
distintos.

## Ejemplo ilustrativo

Escala ilustrativa de 0 a 100 (los pesos exactos se definen al
implementar v1.3, no aquí):

| Candidato | Factores presentes | Score ilustrativo |
|---|---|---|
| "La organización del Festival Vallenato anuncia las fechas del Reinado Infantil 2027" | Anuncio oficial (+30), relacionado al Festival (+20), sin duplicado ni penalización | ~70/100 — alta prioridad |
| "Un acordeonero local hace un cover de una canción conocida" | Sin anuncio oficial, sin tendencia clara, interés limitado | ~20/100 — baja prioridad |
| La misma nota del Festival, detectada de nuevo tres días después por otra fuente que la reprodujo | Anuncio oficial (+30), relacionado al Festival (+20), penalización por noticia vieja (−25), posible duplicado según huella de contenido | ~25/100 o descartado por EP-05 antes de llegar a calcularse el Score |

## Ver también

- [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md) — la comparación completa
  entre Score, Confidence y Freshness.
- [EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md) — dónde
  encaja el cálculo de Score en el flujo completo.
- [docs/adr/ADR-002-editorial-assessment.md](../adr/ADR-002-editorial-assessment.md) —
  por qué Score vive en `EditorialAssessment` y no en `NewsCandidate` ni
  en `Article`.
- [docs/ROADMAP.md](../ROADMAP.md) — v1.3, "AI scoring engine".
