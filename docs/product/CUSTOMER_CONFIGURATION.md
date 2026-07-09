# Configuración por cliente

> Todo lo que, en una plataforma multi-cliente, tendría que poder variar
> de un `MediaOutlet` a otro. Hoy, con un solo cliente, todo esto es
> configuración global en `.env` (ver `config/settings.py`) o está
> hardcodeado en documentación (`docs/editorial/`) — no hay nada
> configurable por cliente todavía, porque no hay más de un cliente. Este
> documento es el inventario de qué habría que mover, no una
> implementación.

## Inventario

| Configurable | Hoy (cliente único) | Futuro (por `MediaOutlet`) | Entidad de dominio |
|---|---|---|---|
| Sitio y credenciales de WordPress | `WORDPRESS_SITE_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` en `.env` | Credenciales por cliente, potencialmente más de un sitio | `MediaOutlet` (vía `CMSPublisher`) |
| Bot y canal de Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` en `.env` | Uno o más canales por cliente | `NotificationChannel` |
| Categorías editoriales | No implementado | Taxonomía propia de cada cliente, mapeada a `Article.category` | `MediaOutlet` |
| Reglas SEO | No implementado | Reglas propias por cliente (ver `docs/editorial/style-guide.md`, Principio 3) | `EditorialRule` |
| Estilo de escritura / tono | Documentado en `docs/editorial/ai-writing-rules.md`, fijo para Portal Vallenato | Tono, longitud y vocabulario propios por cliente | `EditorialRule` |
| Redes sociales | No implementado | Cuentas configuradas por cliente | `SocialAccount` |
| Flujo de publicación | Pipeline fijo en `workflows/` | Pasos habilitables/deshabilitables por cliente (por ejemplo, un cliente sin agente Social) | `MediaOutlet` |
| Reglas editoriales generales | Documentado en `docs/editorial/style-guide.md`, fijo | Conjunto de reglas propio por cliente | `EditorialRule` |
| Proveedor de IA | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` en `.env`, una elección implícita | Proveedor, modelo y presupuesto por cliente | `AIProvider` |
| Idioma | Español, implícito en los prompts | Idioma por cliente, propagado a las plantillas de `prompts/` | `MediaOutlet` |
| Zona horaria | Implícita (UTC internamente — ver `NewsCandidate.discovered_at`) | Zona horaria propia por cliente, para programación y visualización | `MediaOutlet` |
| Branding / logo | No aplica (herramienta interna sin superficie de marca) | Branding propio para cualquier notificación o panel futuro | `MediaOutlet` |

## Cómo se lee esta tabla

La columna "Hoy" no es una carencia — es la configuración correcta para
un cliente único (ver
[docs/product/MVP_SCOPE.md](MVP_SCOPE.md)). La columna "Futuro" es el
inventario de qué necesitará moverse de variables de entorno a datos
persistidos y resueltos en tiempo de ejecución cuando exista más de un
cliente — ver [docs/product/SAAS_EVOLUTION.md](SAAS_EVOLUTION.md), etapa
"True SaaS", punto 2.

## Qué NO implica esta tabla

- No implica que todos estos ítems se configuren al mismo tiempo — cada
  uno entra en alcance con el sprint que lo necesite (ver
  [docs/ROADMAP.md](../ROADMAP.md)).
- No implica una interfaz de configuración (UI) todavía — eso es del
  sprint "Customer configuration" (v1.2) en adelante, y podría empezar
  siendo un archivo de configuración por cliente antes de ser una
  pantalla.
- No implica que cada ítem se vuelva una tabla separada en la base de
  datos — el diseño físico exacto se decide cuando se implemente, no
  aquí.
