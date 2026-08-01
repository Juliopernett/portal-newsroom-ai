# Radar Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 1.

## Responsabilidad

Vigilar continuamente las fuentes configuradas (sitios de noticias, feeds
RSS, etc.) y detectar contenido que sea nuevo, es decir, que no exista ya
en el historial editorial.

El motor de esta detección (`core.services.discovery_engine.DiscoveryEngine`
— agregación, deduplicación por hash y ordenamiento de candidatos) ya
existe desde Sprint 2. Lo que falta para que este agente exista de verdad:
un `ContentSource` real por fuente (RSS, crawler, ...) y la integración
con `Repository` para descartar contra el historial editorial persistido
(el `DiscoveryEngine` solo deduplica dentro de una misma pasada).

## Depende de

- `core.services.discovery_engine.DiscoveryEngine`
- `core.ports.content_source.ContentSource` (uno o más adaptadores reales)
- `core.ports.repository.Repository` (para descartar duplicados contra el
  historial editorial)

## Produce

Un evento `NewsFound` con los candidatos nuevos. Desde Sprint 3A, esto no
va directo al Extractor: un `RadarPublicationInboxAdapter` (ver
[docs/architecture/publication-inbox.md](../../docs/architecture/publication-inbox.md))
mapea cada `NewsCandidate` a un `PublicationRequest` (`origin=RADAR`,
`is_commercial=False`), que converge con los demás canales de entrada
(WhatsApp, entrada manual) antes de llegar al Extractor. `DiscoveryEngine`
en sí no cambia — Radar sigue siendo uno de varios canales de **Publication
Inbox**, no el único punto de entrada del sistema. Ver
[ADR-003](../../docs/adr/ADR-003-publication-inbox.md).
