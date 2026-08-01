"""Composition root.

The only package allowed to know about every other layer (agents,
workflows, database adapters, config). Wires them together at startup.
Currently only wires configuration and logging — agents and workflows will
be connected here starting with docs/ROADMAP.md Fase 1.
"""
