# Visión de producto

> Este documento reposiciona la visión del producto (Sprint 2.2). No
> reemplaza [docs/VISION.md](../VISION.md), que documenta correctamente el
> problema y los principios de diseño desde la perspectiva del MVP de
> Portal Vallenato. Este documento explica el mismo problema desde la
> perspectiva de una plataforma que sirve a más de un cliente.

## Misión

Darle a un equipo editorial de un medio digital independiente la misma
capacidad operativa que hoy solo tienen las cadenas de medios grandes con
equipos de ingeniería propios — sin pedirles que cedan criterio editorial
ni control sobre lo que publican.

## Visión

Ser la capa de inteligencia editorial que cualquier medio digital
independiente pueda adoptar sobre su flujo de trabajo existente (su CMS,
sus canales de notificación, sus redes) sin tener que reconstruirlo desde
cero — empezando por Portal Vallenato como cliente piloto, y extendiéndose
a medios regionales con necesidades editoriales comparables.

## A quién sirve

**Cliente piloto (hoy):** Portal Vallenato — un medio regional con equipo
editorial pequeño, sitio en WordPress, presencia en redes sociales y
coordinación diaria por Telegram.

**Perfil de cliente objetivo (futuro):** medios digitales independientes
o regionales que:

- Ya operan un CMS propio (WordPress es el caso más común, no el único).
- Tienen un equipo editorial reducido, sin capacidad de construir
  herramientas internas de automatización.
- Publican con una cadencia regular (varias notas por día), no volumen
  de nivel agencia de noticias nacional.
- Necesitan mantener control editorial explícito — no buscan
  "auto-publicación", buscan ahorrar tiempo en lo mecánico.

**Explícitamente fuera de este perfil, al menos en un primer momento:**
grandes conglomerados de medios con equipos de ingeniería propios (ya
resuelven este problema internamente) y agregadores que sí quieren
republicar sin revisión humana (eso no es lo que esta plataforma ofrece,
ver más abajo).

## Problemas que resuelve

El mismo problema que documenta [docs/VISION.md](../VISION.md), pero
replicado independientemente en cada medio de este perfil: tiempo
editorial consumido en tareas mecánicas (detectar, extraer, reescribir,
conseguir imágenes, crear el borrador, coordinar al equipo) en lugar de
en trabajo de criterio (verificar, decidir enfoque, garantizar calidad).

Hoy, cada medio de este perfil resuelve esto — si lo resuelve — con
procesos manuales, automatizaciones genéricas mal ajustadas (ver
[docs/product/COMPETITIVE_ADVANTAGES.md](COMPETITIVE_ADVANTAGES.md)), o
no lo resuelve en absoluto. Ninguna de esas opciones entiende que un
borrador no es una publicación.

## Por qué esto NO es un scraper

Un scraper extrae y republica. Su valor está en la velocidad y el
volumen. Esta plataforma **nunca publica automáticamente** — ver
[docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 1 — y su valor está
en la calidad de lo que le entrega a un editor humano para decidir, no en
cuánto contenido logra mover sin supervisión.

Esto no es una limitación temporal a superar en una versión futura. Es la
razón de ser del producto: un scraper que un cliente pudiera configurar
para publicar sin revisión dejaría de ser este producto.

## Por qué esto NO es un plugin de WordPress

Un plugin de WordPress vive dentro de una instalación de WordPress
específica, acoplado a su versión de PHP y su base de datos, instalado
sitio por sitio. Eso impone límites que esta plataforma no acepta:

- No puede orquestar un flujo que cruza varios servicios (una fuente, un
  proveedor de IA, Telegram, redes sociales) como un pipeline coherente
  — un plugin solo controla lo que pasa dentro de `wp-admin`.
- No tiene un modelo de dominio propio (deduplicación por huella de
  contenido, historial editorial auditable, tareas editoriales) — vive
  limitado al modelo de datos de WordPress.
- Cada cliente queda atado a la versión de plugin que instaló, sin una
  ruta natural para evolucionar el producto para todos a la vez.

WordPress es, para esta plataforma, **un adaptador reemplazable**
(`agents/wordpress/`, implementando `core.ports.cms_publisher.CMSPublisher`
— ver [docs/ARCHITECTURE.md](../ARCHITECTURE.md)), no la plataforma en sí.
Si un cliente futuro no usa WordPress, la plataforma no deja de
funcionar — solo cambia el adaptador.

## Por qué esto SÍ es una Plataforma de Inteligencia Editorial

"Inteligencia editorial" es una elección de términos deliberada, distinta
de "automatización":

- **Automatización** ejecuta tareas. **Inteligencia editorial** además
  aplica criterio codificado — deduplicación, reglas editoriales por
  cliente (ver [docs/product/CUSTOMER_CONFIGURATION.md](CUSTOMER_CONFIGURATION.md)),
  y en el futuro, señales de prioridad y calidad — antes de llegarle a un
  humano.
- El producto no compite en "qué tan bien escribe la IA" (una capacidad
  cada vez más genérica entre proveedores). Compite en el flujo completo
  alrededor de esa escritura: detección sin duplicados, contexto de la
  fuente, trazabilidad, y una aprobación humana estructuralmente
  imposible de saltarse.
- Es una plataforma, no una herramienta puntual, porque el mismo motor
  (ver [docs/architecture/discovery-engine.md](../architecture/discovery-engine.md))
  y el mismo modelo de dominio (ver
  [docs/product/DOMAIN_MODEL.md](DOMAIN_MODEL.md)) están pensados desde
  ahora para servir a más de un cliente — aunque hoy solo sirvan a uno.

## Qué no cambia con este reposicionamiento

- El MVP se sigue construyendo para Portal Vallenato, sin desviarse a
  construir multi-tenencia antes de tiempo — ver
  [docs/product/MVP_SCOPE.md](MVP_SCOPE.md).
- Ninguna regla de negocio existente se relaja —
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md) sigue vigente sin cambios.
- La arquitectura Ports & Adapters ya construida (Sprint 1) es exactamente
  lo que hace posible este reposicionamiento sin reescribir nada — ver
  [docs/product/SAAS_EVOLUTION.md](SAAS_EVOLUTION.md).
