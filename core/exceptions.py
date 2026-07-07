"""Domain exception hierarchy.

Every business-rule error raised anywhere in the system should ultimately
inherit from `DomainError`, so callers can catch failures at the right
level of granularity without depending on infrastructure-specific
exceptions (`requests.HTTPError`, `sqlite3.OperationalError`, etc.).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all errors raised by the domain/business layer."""


class DuplicateContentError(DomainError):
    """Raised when a piece of content has already been processed before.

    Backs the "avoid duplicate news" project rule — agents and workflows
    should catch this instead of re-implementing deduplication checks.
    """


class ContentNotFoundError(DomainError):
    """Raised when a referenced piece of content cannot be located."""


class ConfigurationError(DomainError):
    """Raised when required configuration is missing or invalid."""
