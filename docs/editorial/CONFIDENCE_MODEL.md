# Modelo de Confidence

> Este documento también funciona como el punto central de comparación
> entre **Editorial Score**, **Confidence** y **Freshness** — tres
> conceptos fáciles de confundir porque los tres terminan afectando la
> prioridad de una notificación, pero responden preguntas distintas.
> [EDITORIAL_SCORE.md](EDITORIAL_SCORE.md) y
> [FRESHNESS_MODEL.md](FRESHNESS_MODEL.md) se enfocan en su propio
> concepto y remiten aquí para la comparación completa.

## Qué es Confidence

Confidence responde una sola pregunta: **¿qué tan seguros estamos de que
este candidato es real y está correctamente capturado?** No pregunta si
importa, ni si es reciente — pregunta si es cierto y si los datos que
tenemos sobre él son confiables.

**Ya existe en código hoy:** `NewsCandidate.confidence` (`float`, rango
`0.0`–`1.0`), un campo real desde Sprint 2 — ver
`core/entities/news_candidate.py` y
[docs/architecture/discovery-engine.md](../architecture/discovery-engine.md).
Este documento formaliza qué debería determinar ese número, no introduce
un campo nuevo hoy.

**Nota (Sprint 2.3.1):** hacia adelante, Confidence se modela como un
atributo de `EditorialAssessment` — el mismo Value Object que agrupa
Score, Confidence, Freshness, `priority`, `reasoning` y `calculated_at`
(ver [docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md) y
[docs/adr/ADR-002-editorial-assessment.md](../adr/ADR-002-editorial-assessment.md)),
no un campo aislado. `NewsCandidate.confidence` sigue existiendo tal cual
en el código de hoy — su relación exacta con
`EditorialAssessment.confidence` (¿se retira en favor del Value Object?
¿queda como una confianza inicial y `EditorialAssessment` la refina?) es
una decisión de diseño de datos pendiente para cuando se implemente esto,
no resuelta en este documento.

## Qué NO es Confidence

- No es qué tan importante es la noticia — eso es
  [Editorial Score](EDITORIAL_SCORE.md).
- No es qué tan reciente es — eso es [Freshness](FRESHNESS_MODEL.md).
- No es lo mismo que `Source.priority` (también ya implementado, en
  `core/entities/source.py`). `Source.priority` es una preferencia fija
  que un administrador configura una vez para toda una fuente
  ("esta fuente es más importante que aquella, en general"). Confidence
  es una señal dinámica calculada por candidato, en cada detección
  ("este candidato específico se ve confiable").

## Qué determina Confidence

- Si la fuente está marcada como oficial (ver
  [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-03) o de segunda
  mano.
- Si el contenido extraído está completo y bien formado, o es parcial /
  ambiguo.
- El historial de precisión de esa fuente específica (una fuente que
  frecuentemente publica correcciones aporta menos confianza que una que
  no).
- Si el candidato se presenta explícitamente como no confirmado / rumor
  por la fuente misma (ver EP-04).

## Ejemplos

| Candidato | Confidence | Por qué |
|---|---|---|
| Comunicado oficial de la organización del Festival Vallenato anunciando fechas | Alta (≈0.9–1.0) | Fuente oficial, contenido completo, sin ambigüedad |
| Nota de un medio aliado citando "fuentes cercanas al artista" | Media (≈0.5–0.7) | Fuente de segunda mano, contenido verosímil pero no confirmado por la fuente primaria |
| Publicación en redes de un usuario no verificado sobre un rumor de cancelación | Baja (≈0.1–0.3) | Sin confirmación de la fuente, alto riesgo de ser falso |

## Cómo interactúan Score, Confidence y Freshness

| | Editorial Score | Confidence | Freshness |
|---|---|---|---|
| Pregunta que responde | ¿Qué tan importante es, si es cierto? | ¿Qué tan seguros estamos de que es cierto? | ¿Qué tan reciente / urgente es? |
| Quién/qué la determina | Señales de contenido: artista en tendencia, anuncio oficial, exclusividad, festival, engagement — ver [EDITORIAL_SCORE.md](EDITORIAL_SCORE.md) | Confiabilidad de la fuente y calidad de la extracción | Tiempo transcurrido desde publicación/detección — ver [FRESHNESS_MODEL.md](FRESHNESS_MODEL.md) |
| Dónde vive (diseño, Sprint 2.3.1) | Atributo de `EditorialAssessment` (Value Object) | Atributo de `EditorialAssessment`; hoy también existe como campo suelto en `NewsCandidate.confidence` (Sprint 2, ver nota arriba) | Atributo de `EditorialAssessment`, calculado sobre `NewsCandidate.published_at` / `discovered_at`, ya implementados |
| Estado de implementación | Conceptual — planeado para v1.3 ("AI scoring engine") | Parcialmente implementado — `NewsCandidate.confidence` existe; `EditorialAssessment` todavía no | Conceptual |
| Ejemplo de valor alto | Anuncio oficial de un artista en tendencia | Comunicado directo de la fuente oficial | Detectado minutos después de publicado |
| Ejemplo de valor bajo | Nota menor sin relevancia editorial | Rumor sin confirmar de una cuenta no verificada | Detectado varios días después de publicado |

### Ejemplos combinados

- **Score alto + Confidence alta + Freshness alta**: el caso ideal —
  anuncio oficial importante, recién publicado. Notificación inmediata y
  de alta prioridad al editor. Sigue requiriendo aprobación (EP-02).
- **Score alto + Confidence baja**: importante *si es cierto*, pero no
  confirmado — se notifica igual, etiquetado como rumor (EP-04), sin la
  urgencia de "última hora" hasta que se confirme.
- **Score bajo + Freshness alta**: reciente pero menor — notificación de
  baja prioridad, probablemente agrupada con otras en vez de individual.
- **Score alto + Freshness baja**: contenido importante pero no urgente
  (por ejemplo, contenido evergreen sobre la historia del festival) — se
  procesa sin prisa, no compite por atención inmediata con lo urgente.
- **Confidence baja + Score bajo**: candidato de bajo valor en ambos
  ejes — baja prioridad, pero **nunca se descarta en silencio** (ver
  [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-10).

Ver el árbol de decisión completo que usa estas tres señales en
[EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md).

## Qué sigue sin resolver

Ninguno de los tres valores, ni combinados, decide nada por sí solo —
solo ordenan y dan contexto a lo que un editor humano revisa. Ver
[HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).
