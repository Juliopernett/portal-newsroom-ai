# Extractor Agent

**Estado:** Primera implementación real (Sprint Discovery 3,
2026-08-29) — `html_content_extractor.py`, `requests` + `BeautifulSoup`,
sin JavaScript. Deliberadamente no usa Playwright (instalado en
`requirements.txt` pero sin usar) — renderizar JS implica binarios de
navegador en la imagen Docker de Railway, una complejidad de despliegue
que no correspondía a este sprint. Solo extrae lo que ya está en el
HTML servido por el sitio (`<meta>` Open Graph/`article:*`, o
heurísticas simples si no están) — nunca reescribe ni genera texto.

## Responsabilidad

A partir de una referencia de contenido (una URL ya resuelta a la
fuente real — ver `core.services.source_resolution_service`), extraer
el contenido completo de forma estructurada: título, cuerpo, autor,
fecha, medio e imágenes cuando estén disponibles.

## Limitación conocida

Una página que requiere JavaScript para renderizar su contenido (poco
o ningún `<p>` en el HTML servido) no se puede extraer con este
adaptador — `extract()` lanza `ContentExtractorError` en vez de
devolver contenido vacío o inventado. Ver `agents/radar/README.md` para
el hallazgo de la prueba real contra el feed de Google Noticias
(Discovery 3): el paso *anterior* (resolver la URL real) ya falla para
la mayoría de los candidatos actuales, así que este extractor rara vez
llega a ejecutarse hoy — el bloqueo real está un paso atrás.

## Depende de

- `core.ports.content_extractor.ContentExtractor`

## Produce

`core.entities.extracted_content.ExtractedContent`, que se entrega al
agente Writer (Discovery 4+, no implementado).
