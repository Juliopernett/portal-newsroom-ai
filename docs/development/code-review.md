# Code review

## Por qué existe este documento antes de tener un equipo grande

Hoy el proyecto lo mantiene un equipo pequeño. Documentamos el proceso de
revisión desde ahora — no cuando el equipo crezca — para que la barra de
calidad no dependa de quién esté mirando en un momento dado, y para que
cualquier persona que se sume tenga el mismo estándar por escrito desde
el primer Pull Request.

## Qué se revisa

### 1. Correctitud automática (obligatoria, bloquea el merge)

- [ ] `pytest` pasa completo.
- [ ] `ruff check .` sin advertencias.
- [ ] `mypy` en modo estricto sin errores sobre el código de producción
      (`core/`, `agents/`, `workflows/`, `database/`, `config/`, `shared/`,
      `app/`).
- [ ] No se agregaron dependencias nuevas sin justificación en la
      descripción del PR.

### 2. Consistencia arquitectónica (revisión humana)

- ¿El cambio respeta la regla de dependencia — `core/` no importa nada de
  `agents/`, `database/`, `app/` ni SDKs externos? Ver
  [docs/ARCHITECTURE.md](../ARCHITECTURE.md).
- ¿Un agente nuevo depende de un `Protocol` en `core/ports/`, en vez de
  una librería concreta? Ver
  [docs/adr/ADR-001-project-vision.md](../adr/ADR-001-project-vision.md).
- ¿Se evitaron módulos genéricos (`utils.py`, `helpers.py`)? Ver
  [docs/CODING_STANDARDS.md](../CODING_STANDARDS.md).

### 3. Reglas de negocio (revisión humana, no negociable)

- ¿El cambio podría hacer que el sistema publique automáticamente en
  WordPress o en redes sociales, sin aprobación humana? Si hay cualquier
  duda razonable, el PR se rechaza. Ver
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 1.
- ¿Se agregó o cambió una variable de entorno sin declararla en
  `config/settings.py` y `.env.example`?
- ¿Hay contenido duplicado que debería deduplicarse y no lo está?

### 4. Calidad de tests

- ¿Los tests nuevos prueban comportamiento, no implementación? (un
  refactor interno no debería romper tests que solo validan la
  interfaz pública)
- ¿Las pruebas unitarias corren sin red, sin credenciales y sin un
  servicio externo real? Ver
  [docs/CODING_STANDARDS.md](../CODING_STANDARDS.md), sección "Pruebas".
- ¿La cobertura del código nuevo se mantiene alta? (referencia: Sprint 2
  entregó 100% en el código que agregó — ver `CHANGELOG.md`).

### 5. Documentación

- ¿`CHANGELOG.md` refleja el cambio si es notable? Ver
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 10.
- ¿Algún documento de `docs/` quedó desactualizado por este cambio
  (`docs/ARCHITECTURE.md`, un `README.md` de agente, el roadmap)?

## Cómo se aprueba un Pull Request

1. Quien abre el PR marca su propio checklist (arriba) antes de pedir
   revisión — ver [CONTRIBUTING.md](../../CONTRIBUTING.md).
2. Un segundo par de ojos revisa las secciones 2 a 5 (lo que la
   automatización no puede verificar).
3. Si el PR toca `docs/PROJECT_RULES.md` o cambia el comportamiento de
   publicación/notificación, requiere una aprobación explícita adicional,
   sin excepción — es la única regla de revisión que no es negociable
   bajo ninguna circunstancia.
4. Ninguna rama se integra a `develop` con el checklist de la sección 1
   incompleto, sin importar la urgencia.

## Ver también

- [docs/development/branch-strategy.md](branch-strategy.md) — de dónde
  sale y a dónde vuelve la rama que se está revisando.
- [docs/CODING_STANDARDS.md](../CODING_STANDARDS.md) — el detalle de cada
  ítem de estilo y tipado.
