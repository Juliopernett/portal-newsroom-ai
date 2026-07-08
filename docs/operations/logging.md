# Estrategia de logging

## Qué existe hoy

`shared/logger.py` centraliza el logging del proyecto: cada módulo llama
a `get_logger(__name__)` en vez de configurar `logging` por su cuenta.
Hoy escribe a dos destinos:

- **Consola** (`StreamHandler`) — útil en desarrollo y en contenedores
  (donde stdout es lo que la infraestructura recolecta).
- **Archivo rotativo** (`logs/newsroom.log`, 5 MB × 5 backups).

Formato actual: texto plano legible por humanos —
`%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`.

`DiscoveryEngine` ya sigue la regla de negocio de loguear lo relevante
(candidatos recolectados por fuente, duplicados descartados, fuentes
deshabilitadas saltadas) — ver
[docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 6, y
[docs/architecture/discovery-engine.md](../architecture/discovery-engine.md).

## Qué debe registrarse siempre (regla de negocio, no técnica)

Por [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 6, cualquier
acción relevante para el negocio se registra:

- Contenido detectado (por fuente, por pasada).
- Contenido descartado por duplicado.
- Borrador creado en WordPress.
- Notificación enviada al equipo editorial.
- Decisión editorial (aprobación / rechazo) y quién la tomó.
- Cualquier error de integración con un servicio externo (WordPress,
  Telegram, proveedor de IA, una fuente).

Nunca se registran secretos ni credenciales (tokens, contraseñas, API
keys) — ni siquiera en nivel `DEBUG`.

## Cómo evolucionará

A medida que existan más agentes ejecutándose como procesos separados o
en contenedores (ver [docs/deployment/aws.md](../deployment/aws.md)), el
formato de texto plano actual deja de ser suficiente:

1. **Logging estructurado (JSON)** en producción — cada línea de log como
   un objeto con campos fijos (`timestamp`, `level`, `logger`, `message`,
   más contexto), para que una herramienta lo pueda indexar sin parsear
   texto libre. El formato de texto plano actual se mantiene para
   desarrollo local, donde la legibilidad humana importa más.
2. **ID de correlación por pipeline.** Cuando un workflow encadene varios
   agentes (Radar → Extractor → Writer → ...), cada ejecución del
   pipeline debería llevar un identificador único que aparezca en todos
   los logs de esa ejecución, para poder reconstruir "qué le pasó a esta
   noticia específica" sin adivinar por timestamps.
3. **Destino centralizado en la nube.** Los logs de un contenedor en
   ECS/App Runner van a CloudWatch Logs (ver
   [docs/deployment/aws.md](../deployment/aws.md)) en vez de a un archivo
   local — el rotating file handler actual es una solución de desarrollo
   y de despliegue de un solo servidor, no de contenedores efímeros.
4. **Retención definida.** Una política explícita de cuánto tiempo se
   conservan los logs (hoy: 5 archivos de 5 MB, sin política de
   retención por tiempo) — a definir junto con la estrategia de AWS.
5. **Alertas sobre errores.** Cuando un error de integración se repite o
   supera un umbral, el equipo técnico debería enterarse sin tener que
   revisar logs manualmente — mecanismo concreto (CloudWatch Alarms, u
   otro) a decidir en el sprint de despliegue.

Nada de esto está implementado. `shared/logger.py` sigue siendo el único
punto de entrada al logging del proyecto — cuando estas mejoras se
implementen, deberían seguir viviendo detrás de esa misma interfaz
(`get_logger`), sin que cada módulo que ya la usa tenga que cambiar.

## Ver también

- [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 6.
- [docs/deployment/aws.md](../deployment/aws.md) — dónde terminarán
  viviendo estos logs en producción.
