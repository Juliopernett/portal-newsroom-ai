# Telegram Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 4.

## Responsabilidad

Notificar al equipo editorial vía Telegram cuando un borrador está listo
para revisión, y registrar la decisión de aprobación/rechazo que el equipo
tome.

## Depende de

- `core.ports.notifier.Notifier`

## Produce

Notificaciones entregadas y decisiones editoriales registradas en el
historial (`core.ports.repository.Repository`).
