# Contribuir a Portal Newsroom AI

## Configuración del entorno

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
pytest
```

## Flujo de trabajo

1. Crea una rama descriptiva a partir de `main`:
   - `feature/<nombre-corto>` para funcionalidad nueva.
   - `fix/<nombre-corto>` para correcciones.
   - `docs/<nombre-corto>` para documentación.
   - `chore/<nombre-corto>` para mantenimiento (dependencias, configuración).
2. Realiza commits pequeños y descriptivos, siguiendo
   [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
3. Antes de abrir un Pull Request, verifica:
   - [ ] `pytest` pasa sin errores.
   - [ ] `ruff check .` sin advertencias.
   - [ ] `mypy .` sin errores.
   - [ ] Las funciones/clases públicas nuevas tienen docstring.
   - [ ] Se actualizó `CHANGELOG.md` si el cambio es notable.
   - [ ] Se actualizó la documentación relevante en `docs/` si aplica.
4. Describe en el PR **qué** cambia y **por qué**, no solo el detalle técnico.

## Cómo agregar un nuevo agente

Cada agente vive en `agents/<nombre>/` y sigue el mismo patrón:

1. Define (o reutiliza) el contrato que necesita en `core/ports/`.
2. Implementa el agente en `agents/<nombre>/` dependiendo únicamente de ese
   contrato, nunca de una librería externa concreta directamente.
3. Si el agente necesita persistencia, agrega el adaptador correspondiente en
   `database/repositories/` implementando el port de `core/ports/repository.py`.
4. Agrega pruebas en `tests/unit/agents/<nombre>/`.
5. Si el agente se conecta a un pipeline, exprésalo en `workflows/`.
6. Actualiza `docs/ROADMAP.md` marcando la fase correspondiente.

Consulta [PROJECT_RULES.md](docs/PROJECT_RULES.md) y
[CODING_STANDARDS.md](docs/CODING_STANDARDS.md) antes de escribir código.

## Reglas no negociables

Antes de contribuir, lee [PROJECT_RULES.md](docs/PROJECT_RULES.md). La regla
más importante: **el sistema nunca publica automáticamente**. Cualquier
cambio que rompa esa garantía será rechazado.
