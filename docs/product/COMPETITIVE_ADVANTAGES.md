# Diferenciación competitiva

> El argumento central de este documento: la diferenciación no está en
> ninguna capacidad de IA puntual — eso se comoditiza con el tiempo entre
> proveedores. Está en el flujo editorial completo, con un punto de
> aprobación humana que es estructuralmente imposible de saltear. Ver
> [docs/product/PRODUCT_VISION.md](PRODUCT_VISION.md), sección "Por qué
> esto SÍ es una Plataforma de Inteligencia Editorial".

## Frente a lectores de RSS (Feedly y similares)

Un lector de RSS agrega y muestra contenido para que una persona lo
consuma. No reescribe, no conoce el estilo editorial de un medio, no se
integra con un CMS, y no tiene noción de "esto es un borrador esperando
revisión" — es una herramienta de consumo, no de producción editorial.

Esta plataforma usa el mismo tipo de fuente (`core.ports.content_source.ContentSource`,
ver [docs/architecture/discovery-engine.md](../architecture/discovery-engine.md))
como punto de partida, pero el resultado de detectar una noticia es un
`NewsCandidate` que entra a un pipeline editorial completo — extracción,
reescritura, SEO, imágenes, borrador, notificación, aprobación — no un
ítem más en una lista para leer.

## Frente a plugins de WordPress

Un plugin vive dentro de una instalación de WordPress, acoplado a su
versión y su base de datos, instalado sitio por sitio. Eso impone tres
límites que esta plataforma no tiene:

- No puede orquestar un flujo que cruza varios servicios (fuente,
  proveedor de IA, Telegram, redes) como un pipeline coherente.
- No tiene modelo de dominio propio (deduplicación por huella de
  contenido, historial editorial, tareas editoriales) — vive limitado al
  modelo de datos de WordPress.
- Cada cliente queda atado a la versión instalada; no hay una ruta
  natural para que un producto evolucione para todos los clientes a la
  vez.

Ver [docs/product/PRODUCT_VISION.md](PRODUCT_VISION.md), sección "Por
qué esto NO es un plugin de WordPress", para el detalle completo.

## Frente a automatizaciones genéricas (Zapier y similares)

Zapier y herramientas equivalentes son excelentes para automatizaciones
puntuales ("si pasa X, hacé Y"). Lo que no tienen es un **modelo de
dominio editorial**: no saben qué es un duplicado por contenido, no
distinguen un borrador de una publicación, no tienen el concepto de una
tarea editorial asignada a una persona.

Construir este flujo en una herramienta de automatización genérica
significa reinventar ese modelo de dominio dentro de una herramienta que
no fue diseñada para sostenerlo — y, más importante, no ofrece ninguna
garantía estructural de que "nunca se publica sin aprobación humana" se
mantenga: un Zap se puede reconfigurar para saltarse ese paso en
cualquier momento, porque la herramienta no sabe que ese paso es
sagrado. En esta plataforma, esa garantía está en la arquitectura misma
— ningún `CMSPublisher` expone un método de publicar, solo de crear
borradores (ver [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 1) —
no es una convención que alguien pueda desactivar con un clic.

## Frente a "escritores de IA" simples

Un asistente de IA que reescribe texto resuelve un paso — el que aquí
corresponde al agente Writer. No hace descubrimiento, no deduplica, no
conoce el estilo del medio de forma persistente, no crea el borrador en
el CMS, no notifica al equipo, no rastrea la decisión editorial. Es un
componente, no un flujo de trabajo.

El valor de esta plataforma no depende de que un modelo de IA en
particular escriba mejor que otro — de hecho, el proveedor de IA es
deliberadamente un adaptador reemplazable
(`core.ports.ai_provider.AIProvider`), no un compromiso con un proveedor
específico. El valor está en todo lo que rodea a esa escritura: qué se
detecta, qué se descarta por duplicado, cómo se le presenta a un editor,
y qué pasa con su decisión.

## El argumento central, en una frase

Cualquiera de estos competidores puede automatizar un paso. Ninguno
modela el flujo editorial completo con una aprobación humana como
garantía estructural, no como buena práctica que depende de que alguien
la respete.
