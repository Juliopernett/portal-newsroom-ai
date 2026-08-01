# Integration tests

Pruebas que ejercitan adaptadores reales — I/O real, aunque sea contra un
doble de prueba — a diferencia de `tests/unit/`, donde se prueban los
servicios de dominio contra dobles puramente en memoria.

Hoy: `test_fake_content_source.py` (lectura real de archivos en
`tests/fixtures/*.json`) y `test_discovery_engine_with_fixtures.py`
(`DiscoveryEngine` de punta a punta sobre esos mismos archivos).

A partir de docs/ROADMAP.md Fase 1, también vivirán aquí las pruebas de
repositorios reales contra una base de datos SQLite de prueba.
