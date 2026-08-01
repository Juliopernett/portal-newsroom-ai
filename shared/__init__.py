"""Cross-cutting technical utilities shared by the whole codebase.

Anything here must be infrastructure-agnostic and free of business rules —
business rules belong in `core/`. Today: centralized logging
(`shared.logger`).
"""
