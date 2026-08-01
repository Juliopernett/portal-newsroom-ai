# Human in the Loop

> Este es el principio raíz del que se derivan todos los demás documentos
> de `docs/editorial/`: [EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md),
> [EDITORIAL_SCORE.md](EDITORIAL_SCORE.md),
> [CONFIDENCE_MODEL.md](CONFIDENCE_MODEL.md),
> [FRESHNESS_MODEL.md](FRESHNESS_MODEL.md),
> [EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md) y
> [NEWS_LIFECYCLE.md](NEWS_LIFECYCLE.md) asumen este principio como dado,
> no lo repiten. Si algo en esos documentos parece contradecirlo, este
> documento tiene precedencia.

## El principio

**La IA asiste. El editor decide.**

No es un eslogan — es una restricción de diseño con consecuencias
concretas en cada documento de esta carpeta: ningún cálculo (Score,
Confidence, Freshness) toma una decisión de publicación por sí mismo;
todos existen únicamente para darle a un editor humano mejor información,
más rápido, para que decida él.

## Por qué existe

Sin este principio, cada documento que sigue sería una especificación de
automatización. Con él, son una especificación de **asistencia** — la
diferencia no es semántica: define qué se le permite construir a un
futuro agente de IA y qué no, sin importar cuán buena sea su capacidad
técnica. Ver
[docs/product/PRODUCT_VISION.md](../product/PRODUCT_VISION.md), sección
"Por qué esto NO es un scraper".

## Qué puede hacer la IA

- Detectar contenido nuevo (Discovery Engine).
- Extraer contenido estructurado de una fuente.
- Calcular una huella de duplicado (ver
  [docs/architecture/discovery-engine.md](../architecture/discovery-engine.md)).
- Calcular una `EditorialAssessment` sobre un candidato — Score,
  Confidence, Freshness, `priority` y `reasoning` (ver
  [docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md) y los
  documentos correspondientes). Una `EditorialAssessment` **asiste** al
  editor dándole contexto legible (el campo `reasoning` existe
  precisamente para eso) — nunca decide por él. Recalcularla tantas
  veces como haga falta no cambia esto: cada recálculo sigue siendo
  información para un humano, nunca una decisión tomada en su lugar. Ver
  [docs/adr/ADR-002-editorial-assessment.md](../adr/ADR-002-editorial-assessment.md).
- Redactar un borrador de artículo, respetando
  [docs/editorial/ai-writing-rules.md](ai-writing-rules.md).
- Sugerir metadatos SEO.
- Sugerir copys para redes sociales.
- Notificar a un editor de que algo requiere su atención.
- Priorizar el orden en que se le presentan candidatos a un editor —
  nunca decidir cuáles no le llegan.

## Qué la IA nunca puede hacer

- Publicar un artículo. Ningún adaptador de CMS expone un método de
  publicar, solo de crear borradores — ver
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 1.
- Inventar una cita que la fuente no dijo.
- Fabricar un hecho, cifra o dato que no esté en el contenido extraído.
- Aprobar o rechazar su propio borrador.
- Descartar un candidato de forma silenciosa y definitiva — un
  descarte (por duplicado, por baja relevancia) siempre queda
  registrado en el historial editorial, nunca desaparece sin dejar
  rastro. Ver [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 11.
- Publicar en redes sociales sin aprobación — misma regla que WordPress.
- Decidir que una fuente es confiable de forma permanente sin que un
  humano lo haya confirmado alguna vez.

## Qué decide siempre un editor humano

- Aprobar, rechazar o pedir cambios sobre un borrador.
- La redacción final de cualquier artículo que se publique.
- Cuándo publicar (ahora o programado), no solo si publicar.
- Si una fuente marcada como rumor queda confirmada o descartada.
- Si un patrón de falsos positivos (duplicados mal detectados,
  candidatos irrelevantes con Score alto) amerita ajustar la
  configuración de una fuente.

## Responsabilidades

| Actor | Responsabilidad |
|---|---|
| Discovery Engine / futuros agentes de IA | Reducir el trabajo mecánico antes de que llegue a un humano: detectar, deduplicar, extraer, calificar, redactar un borrador, sugerir. |
| Editor humano | Ejercer criterio: verificar, decidir, aprobar, corregir, publicar. |
| La plataforma (como sistema) | Garantizar estructuralmente que el primer grupo nunca pueda sustituir al segundo — no como política de uso, sino como límite de lo que el software permite hacer. |

## Ejemplo

Un candidato con una `EditorialAssessment` favorable (Score alto —
anuncio oficial de un artista en tendencia; Confidence alta — fuente
oficial verificada; Freshness alta — detectado minutos después de
publicado) — el caso "ideal" — **sigue** necesitando aprobación humana
antes de convertirse en un borrador de WordPress. La diferencia con una
`EditorialAssessment` desfavorable no es si un humano interviene, es
cuánta prioridad y contexto (vía `reasoning`) tiene ese humano al
revisarlo — ver
[docs/editorial/EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md).
