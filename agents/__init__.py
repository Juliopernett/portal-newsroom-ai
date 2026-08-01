"""Application layer: one package per agent responsibility.

Each agent depends only on the `core.ports` contracts it needs, never on a
concrete external library or another agent directly. Cross-agent
coordination belongs in `workflows/`, not here. See docs/ARCHITECTURE.md.
"""
