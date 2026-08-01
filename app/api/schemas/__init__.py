"""Pydantic request/response schemas for the internal API.

Separate from `core/entities/` on purpose: these describe the HTTP
contract, not the domain. A domain entity gaining a field it doesn't want
to expose over HTTP (or vice versa) should never force a change here or
there — the two are translated explicitly in `app/api/routers/`.
"""
