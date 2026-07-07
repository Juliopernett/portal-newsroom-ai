# AI Orchestrator Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 8.

## Responsabilidad

Coordinar de forma inteligente y dinámica el conjunto de agentes (Radar,
Extractor, Writer, SEO, Images, WordPress, Telegram, Social, Analytics),
decidiendo qué agentes ejecutar y en qué orden según el tipo de contenido
detectado.

Se diferencia de `workflows/` en que un workflow es una secuencia fija
definida por el equipo técnico, mientras que el orquestador puede tomar
decisiones dinámicas basadas en el contenido.

## Depende de

- Los `ports` de todos los agentes que coordina.

## Produce

La ejecución coordinada de un pipeline editorial completo, siempre
terminando en un borrador + notificación, nunca en una publicación
automática.
