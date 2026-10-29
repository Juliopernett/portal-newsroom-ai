"""Run one discovery pass over every enabled Radar source (forced), and report it.

Sprint Discovery 1 (2026-08-25) created this for the single Google News feed;
since Sprint Fuentes (2026-10-29) sources live in the `sources` table and the
real job is `scripts/escanear_fuentes.py`. This stays as a thin alias so any
existing habit or note keeps working: it is `escanear_fuentes --forzar`.

Usage:
    python -m scripts.descubrir_noticias
"""

from __future__ import annotations

import sys

from scripts.escanear_fuentes import main

if __name__ == "__main__":
    sys.argv.append("--forzar")
    main()
