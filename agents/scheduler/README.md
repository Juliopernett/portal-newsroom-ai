# Scheduler Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 6.

## Responsabilidad

Ejecutar de forma programada y periódica los pipelines definidos en
`workflows/` (por ejemplo: "revisar fuentes cada 15 minutos").

## Depende de

- Los pipelines expuestos por `workflows/`, no de agentes individuales
  directamente.

## Produce

Ejecuciones periódicas de los workflows configurados.
