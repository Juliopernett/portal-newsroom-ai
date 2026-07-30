"""Domain service: content fingerprinting for deduplication.

Defines what makes two discovered items "the same piece of news" as a
pure function, so every `core.ports.content_source.ContentSource` adapter
computes fingerprints the same way instead of inventing its own — see
docs/PROJECT_RULES.md, rule 11.
"""

from __future__ import annotations

import hashlib


def generate_candidate_hash(source: str, url: str) -> str:
    """Return a stable fingerprint for a candidate from `source` at `url`.

    Two candidates with the same source and URL are considered the same
    piece of news, even if their title or summary differ slightly between
    scans.
    """
    fingerprint = f"{source.strip().lower()}:{url.strip().lower()}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
