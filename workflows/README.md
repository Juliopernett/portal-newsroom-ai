# Workflows

Vacío intencionalmente durante la fase Foundation.

Aquí se compondrán los pipelines editoriales completos, encadenando
agentes en una secuencia fija (por ejemplo, `new_article_pipeline.py`:
Radar → Extractor → Writer → SEO → Images → WordPress(borrador) →
Telegram(notificación)).

Un workflow es una secuencia **determinística**, decidida por el equipo
técnico. Se diferencia del agente `agents/orchestrator/` (AI Orchestrator),
que puede decidir dinámicamente qué agentes ejecutar según el contenido.

Ver docs/ARCHITECTURE.md, sección "Flujo de datos previsto".
