"""Internal REST API (Sprint 3D).

A minimal HTTP surface over the Commercial Core (`Client`, `Pauta`,
`PublicationRequest`) built in Sprint 3B/3C — the first way to operate
the domain without writing Python. No authentication, no permissions, no
pagination, no filtering: none of that has a real requirement yet, see
docs/PROJECT_RULES.md and the KISS principle already applied throughout
this project.

This package is part of `app/`, the composition root — the only layer
allowed to know about `core/`, `database/` and a web framework all at
once. `core/` has no idea this package exists.
"""
