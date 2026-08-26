# core/services

## Qué vive aquí

Servicios de dominio: lógica de negocio pura que no pertenece naturalmente
a una única entidad y por lo tanto no encaja como método de un modelo de
`core/entities/`.

- `deduplication.py`: `generate_candidate_hash`, la huella de contenido
  que decide si dos candidatos son "la misma noticia" (Sprint 2).
- `discovery_engine.py`: `DiscoveryEngine`, el motor que agrega, deduplica
  y ordena candidatos provenientes de varias fuentes (Sprint 2). Ver
  docs/ARCHITECTURE.md, sección "Discovery Engine".
- `radar_service.py`: `descubrir`, corre una pasada de `DiscoveryEngine`
  sobre una fuente y persiste solo los `NewsCandidate` que
  `NewsCandidateRepository` no conocía todavía — la deduplicación *entre*
  ejecuciones que `DiscoveryEngine` deliberadamente no hace (Sprint
  Discovery 1, 2026-08-25). Ver `agents/radar/README.md`.
- `news_candidate_service.py`: `guardar`/`descartar`/`crear_noticia`,
  transiciones puras de `EstadoNewsCandidate` sobre un `NewsCandidate`
  (`ValueError` si ya está en un estado terminal — mismo patrón que
  `destino_publicacion_service.py`); `ordenar_para_revision`, ordena
  para el Radar Editorial (nuevos primero, luego más recientes). Sprint
  Discovery 2, 2026-08-26.
- `pauta_service.py`: `PautaService`, calcula cupo consumido/restante y
  vigencia/vencimiento de una `Pauta` (Sprint 3B — Commercial Core MVP).
  Todo calculado a partir de `Pauta` y su historial de
  `PublicationRequest`; nunca un contador almacenado.
- `publication_request_service.py`: `mark_as_published`, la única
  transición de estado de `PublicationRequest` que este sprint necesita
  (Sprint 3B).

Ejemplos de lo que llegará aquí en sprints futuros:

- Reglas de aprobación editorial que dependan de más de una entidad.

## Qué NO vive aquí

- Lógica de acceso a infraestructura (HTTP, base de datos, sistema de
  archivos) — eso vive en los adaptadores (`database/`, y los futuros
  adaptadores dentro de cada agente).
- Orquestación de múltiples agentes — eso vive en `workflows/`.
- Lógica específica de un solo agente — eso vive dentro de ese agente.

## Cómo se usan

Un servicio de dominio recibe sus dependencias ya resueltas contra los
contratos de `core/ports/` (inyectadas desde `app/` o desde el agente que
lo invoca) — nunca instancia un adaptador concreto por su cuenta. Esto los
mantiene testeables sin infraestructura real, igual que los agentes (ver
docs/PROJECT_RULES.md, regla 5).
