"""Centralized configuration package.

`config.settings.get_settings()` is the single source of truth for
configuration across the whole project. No other module should read
`os.environ` directly (see docs/PROJECT_RULES.md).
"""
