"""Test doubles (fakes) for core.ports.

Not part of production code — never imported by app/, agents/, or
workflows/. Exists purely so tests can exercise domain services without
network access, external APIs, or a database. See fake_content_source.py
and tests/fixtures/.
"""
