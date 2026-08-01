"""Editorial pipelines: deterministic composition of agents.

A workflow chains agents in a fixed, business-defined sequence (e.g.
Radar -> Extractor -> Writer -> SEO -> Images -> WordPress draft ->
Telegram notification). See README.md in this package and
docs/ARCHITECTURE.md for how this differs from `agents/orchestrator/`.
"""
