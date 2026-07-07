"""Ports: contracts the domain and agents depend on.

Each port is a `typing.Protocol` describing *what* an agent needs, never
*how* it is fulfilled. Concrete adapters (a WordPress client, a Telegram
bot, an OpenAI/Anthropic client, a SQLAlchemy repository, ...) implement
these protocols in their own module and are wired together in `app/`.

This indirection is what makes "swap WordPress for another CMS" or "stop
using Telegram" a local, single-module change instead of a rewrite.
"""
