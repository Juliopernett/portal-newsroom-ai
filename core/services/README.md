# core/services

Vacío intencionalmente durante este sprint (Foundation Hardening).

## Qué vive aquí

Servicios de dominio: lógica de negocio pura que no pertenece naturalmente
a una única entidad y por lo tanto no encaja como método de un modelo de
`core/entities/`. Ejemplos de lo que llegará aquí a partir de Sprint 2+:

- Reglas de deduplicación que combinan más de una fuente de información
  (por ejemplo, decidir si dos referencias distintas son "la misma
  noticia").
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
