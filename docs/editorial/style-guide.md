# Guía de estilo editorial

> Principios editoriales de Portal Vallenato que rigen tanto al equipo
> humano como a cualquier contenido que el futuro agente Writer genere.
> Para las reglas específicas de cómo debe escribir la IA, ver
> [docs/editorial/ai-writing-rules.md](ai-writing-rules.md).

## Principio 1 — No inventar hechos

Ningún dato, cita, cifra o afirmación puede aparecer en un artículo si no
está presente en el material fuente. Si la fuente es ambigua o
incompleta, el artículo debe reflejar esa ambigüedad — no rellenarla con
una suposición razonable. Esto aplica igual a un editor humano
reescribiendo a mano que a un texto generado por IA.

Consecuencia práctica para el sistema: el futuro agente Writer debe
poder señalar cuándo no tiene suficiente información, en vez de producir
un texto fluido pero inventado. Un borrador incompleto y honesto es
preferible a uno completo y fabricado.

## Principio 2 — No clickbait

El titular debe describir con precisión lo que el artículo contiene. Se
evita:

- Titulares que prometen información que el cuerpo no entrega ("No vas a
  creer lo que pasó...").
- Preguntas retóricas usadas para ocultar la respuesta y forzar el clic.
- Exageración o sensacionalismo sobre hechos verificables.

Un titular fuerte y honesto es un objetivo válido; un titular engañoso
no, sin importar cuánto mejore una métrica de clics.

## Principio 3 — SEO responsable

Optimizar para buscadores es legítimo y necesario, pero nunca a costa de
la Regla 2. SEO responsable significa:

- Palabras clave relevantes al contenido real del artículo, no
  insertadas artificialmente donde no aportan sentido.
- Meta descripciones que resumen el artículo con precisión, no que
  prometen algo distinto para mejorar el CTR.
- Un slug y una estructura de URL claros, legibles y estables (no se
  cambian una vez publicados, para no romper enlaces existentes).

## Principio 4 — Respeto por las fuentes

- Toda noticia reescrita debe atribuir su fuente original de forma
  visible.
- Reescribir no es copiar: el estilo y la estructura del texto deben ser
  propios de Portal Vallenato, no una paráfrasis mínima del original.
- Si la fuente pide corrección o retractación, el artículo se actualiza
  o retira — no se ignora.
- No se reescribe contenido de fuentes cuya fiabilidad no se pueda
  verificar razonablemente.

## Principio 5 — Corrección y transparencia

- Los errores se corrigen tan pronto se detectan.
- Un cambio sustancial después de publicar (no una corrección menor de
  redacción) se señala como tal, no se reemplaza en silencio.

## Cómo se aplican estos principios hoy

Ninguno de estos principios está todavía codificado en el sistema — no
existe agente Writer, SEO ni WordPress (ver
[docs/roadmap/v1-roadmap.md](../roadmap/v1-roadmap.md)). Este documento
es la referencia que el equipo editorial usa hoy para trabajo manual, y
la especificación que las plantillas de `prompts/` (ver
`prompts/README.md`) deberán respetar cuando esos agentes se construyan.
