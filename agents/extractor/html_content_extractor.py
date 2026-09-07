"""Real `ContentExtractor` adapter for plain (non-JavaScript) HTML pages.

Sprint Discovery 3 (2026-08-29) — the first real Extractor implementation
this project has (see `agents/extractor/README.md`). Deliberately
minimal: `requests` + `BeautifulSoup`, reads standard `<meta>` tags
(Open Graph / `article:*`) where available and falls back to simple
heuristics (`<article>` tag, or the densest block of `<p>` text) when
they are not. No JavaScript rendering (Playwright is not used here — see
`agents/extractor/README.md` for why) and no rewriting of any kind: this
extracts the page's own words as-is, never generates new text.
"""

from __future__ import annotations

from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from core.entities.extracted_content import ExtractedContent
from core.ports.content_extractor import ContentExtractorError
from shared.logger import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 20
_MIN_BODY_CHARS = 200


class HtmlContentExtractor:
    """`ContentExtractor` implemented against plain server-rendered HTML."""

    def __init__(self, *, timeout: int = _REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    def extract(self, reference: str) -> ExtractedContent:
        """Fetch `reference` and extract its title/body/author/date/images.

        Raises `ContentExtractorError` if the page can't be fetched, or
        if fetched content is too short to be a real article (a common
        signature of a page that needs JavaScript to render — this
        extractor cannot run one, see the module docstring).
        """
        try:
            response = requests.get(
                reference,
                timeout=self._timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PortalNewsroomAI/1.0)"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ContentExtractorError(f"No se pudo obtener '{reference}': {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")

        title = _extract_title(soup)
        body = _extract_body(soup)
        if not title or not body or len(body) < _MIN_BODY_CHARS:
            raise ContentExtractorError(
                f"No se encontró contenido reconocible en '{reference}' "
                "(la página puede requerir JavaScript o no ser un artículo)"
            )

        return ExtractedContent(
            title=title,
            body=body,
            source_url=reference,
            author=_extract_meta(soup, "author") or _extract_meta(soup, "article:author"),
            published_at=_extract_published_at(soup),
            site_name=_extract_meta(soup, "og:site_name"),
            image_urls=_extract_image_urls(soup),
        )


def _extract_meta(soup: BeautifulSoup, key: str) -> str | None:
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    if isinstance(tag, Tag):
        content = tag.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def _extract_title(soup: BeautifulSoup) -> str | None:
    og_title = _extract_meta(soup, "og:title")
    if og_title:
        return og_title
    if soup.title and soup.title.string:
        return str(soup.title.string).strip()
    return None


def _extract_body(soup: BeautifulSoup) -> str | None:
    article = soup.find("article")
    if isinstance(article, Tag):
        text = _paragraphs_text(article)
        if text:
            return text

    # Fallback: the container whose direct-and-nested <p> tags add up to
    # the most text — a generic "densest block" heuristic for pages
    # without a real <article> tag.
    best_container: Tag | None = None
    best_length = 0
    for container in soup.find_all(["div", "section", "main"]):
        if not isinstance(container, Tag):
            continue
        text = _paragraphs_text(container)
        if len(text) > best_length:
            best_length = len(text)
            best_container = container
    if best_container is not None:
        text = _paragraphs_text(best_container)
        if text:
            return text

    # Last resort: every <p> on the page.
    return _paragraphs_text(soup) or None


def _paragraphs_text(container: Tag) -> str:
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    return "\n\n".join(p for p in paragraphs if p)


def _extract_published_at(soup: BeautifulSoup) -> datetime | None:
    raw = _extract_meta(soup, "article:published_time")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("No se pudo interpretar article:published_time=%r", raw)
        return None


def _extract_image_urls(soup: BeautifulSoup) -> tuple[str, ...]:
    urls: list[str] = []
    for tag in soup.find_all("meta", attrs={"property": "og:image"}):
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, str) and content.strip():
                urls.append(content.strip())
    return tuple(dict.fromkeys(urls))  # de-dup, preserve order
