# Visión del proyecto

> **Nota (Sprint 2.2):** este documento describe correctamente el
> problema y los principios de diseño del MVP. La afirmación "no es un
> producto genérico multi-cliente" en la sección "Qué NO es" describía la
> intención original del proyecto y ya no es exacta: Portal Vallenato
> pasó a ser el **cliente piloto** de una plataforma pensada para servir
> a más de un medio a futuro, sin que eso cambie el alcance del MVP. Ver
> [docs/product/PRODUCT_VISION.md](product/PRODUCT_VISION.md) para la
> visión de producto vigente.
>
> **Nota (Sprint 3A):** la sección "Qué es Portal Newsroom AI" describe el
> flujo orgánico (Radar → Extractor → ... ) como si fuera la única fuente
> de contenido. En la práctica, para el cliente piloto, la mayoría de las
> publicaciones **no** se originan ahí: llegan directamente por WhatsApp
> desde managers, artistas y empresas — contenido comercial, no
> descubierto. El problema de negocio que resuelve el proyecto no cambió
> (ahorrar tiempo mecánico, nunca reemplazar criterio editorial), pero su
> alcance se amplió para incluir la gestión de esas solicitudes
> comerciales. Ver
> [docs/product/PRODUCT_VISION.md](product/PRODUCT_VISION.md), sección
> "Repositioning comercial", y
> [ADR-003](adr/ADR-003-publication-inbox.md) /
> [ADR-004](adr/ADR-004-commercial-manager.md) para el diseño completo.

## Problema

El equipo editorial de Portal Vallenato dedica una parte significativa de su
tiempo a tareas repetitivas y mecánicas: detectar noticias relevantes,
extraer su contenido, reescribirlas con el estilo editorial del medio,
buscar y preparar imágenes, crear el borrador en WordPress, redactar copys
para redes sociales y coordinar al equipo. Ese tiempo se resta del trabajo
que sí requiere criterio humano: verificar fuentes, decidir enfoque
editorial, y garantizar calidad periodística.

## Qué es Portal Newsroom AI

Un sistema de agentes especializados que automatiza el trabajo mecánico del
flujo editorial y deja al equipo humano el trabajo de criterio: revisar,
corregir y aprobar.

Portal Newsroom AI:

- Recibe contenido por varios canales — WhatsApp de managers/artistas/
  empresas, detección automática (Radar), entrada manual — y lo convierte
  en una solicitud de publicación única (ver Nota Sprint 3A abajo).
- Detecta noticias nuevas de las fuentes configuradas.
- Extrae su contenido de forma estructurada.
- Reescribe el artículo con el estilo editorial de Portal Vallenato.
- Descarga y organiza las imágenes asociadas.
- Prepara un **borrador** en WordPress — nunca una publicación.
- Genera propuestas de contenido para redes sociales.
- Notifica al equipo editorial vía Telegram para que revise y decida.
- Evita procesar la misma noticia dos veces.
- Mantiene un historial editorial auditable de todo lo procesado.

## Qué NO es

- **No es un sistema de publicación automática.** Ninguna noticia se publica
  sin que una persona del equipo editorial la revise y apruebe
  explícitamente. Esta es la regla más importante del proyecto — ver
  [PROJECT_RULES.md](PROJECT_RULES.md).
- No reemplaza el criterio editorial humano: reescribe y sugiere, no decide
  qué es noticia ni qué se publica.
- ~~No es un producto genérico multi-cliente. Es una herramienta interna,
  construida a medida del flujo de trabajo de Portal Vallenato.~~
  **Actualizado en Sprint 2.2:** el MVP sigue construyéndose a medida del
  flujo de trabajo de Portal Vallenato, pero como cliente piloto de una
  plataforma pensada para servir a más de un medio — ver
  [docs/product/PRODUCT_VISION.md](product/PRODUCT_VISION.md).

## A quién sirve

Al equipo editorial de Portal Vallenato: periodistas, editores y quien
gestione las redes sociales y el sitio WordPress del medio. El sistema se
diseña para que lo use el equipo día a día, no para que lo opere un
desarrollador.

## Principios que guían el diseño

1. **Ahorrar tiempo, no reemplazar juicio.** Cada agente automatiza una tarea
   mecánica específica; la decisión final siempre es humana.
2. **Módulos reemplazables.** Ninguna integración externa (WordPress,
   Telegram, un proveedor de IA) debe quedar entrelazada con la lógica de
   negocio. Cambiar de proveedor debe ser un cambio local, no una reescritura.
3. **Transparencia y trazabilidad.** Todo lo que el sistema hace debe quedar
   registrado: qué detectó, qué generó, qué se aprobó y qué no.
4. **Crecimiento incremental.** El sistema se construye agente por agente,
   cada uno entregando valor por sí solo, sin depender de que "todo" esté
   terminado para ser útil.

## Visión de largo plazo

Un "newsroom" asistido por múltiples agentes de IA coordinados por un
orquestador central, donde el equipo editorial revisa y aprueba trabajo ya
preparado en lugar de partir de cero en cada noticia — manteniendo siempre
el control editorial humano como última palabra.
