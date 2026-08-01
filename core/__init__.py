"""Domain layer.

Contains only business rules, contracts (`core.ports`) and domain
exceptions. This package must never import infrastructure code
(SQLAlchemy, requests, Playwright, WordPress/Telegram SDKs, ...).
"""
