"""The artist grid also yields each artist's photo (used by the weekly chart cards)."""

from __future__ import annotations

from agents.portal.catalogo_artistas import CatalogoArtistas, parsear_catalogo, parsear_fotos

_WEB = "https://portalvallenato.com"
_HTML = (
    f'<li data-n="silvestre dangond" data-notas="9"><a href="{_WEB}/silvestre-dangond/">'
    f'<img decoding="async" src="{_WEB}/wp-content/uploads/2026/01/silvestre.webp" alt="S">'
    "<span>Silvestre</span></a></li>"
    f'<li data-n="sin foto" data-notas="1"><a href="{_WEB}/sin-foto/">'
    "<span>Sin foto</span></a></li>"
    f'<li data-n="foto ajena" data-notas="1"><a href="{_WEB}/foto-ajena/">'
    '<img src="https://otro-sitio.com/x.jpg"><span>Ajena</span></a></li>'
)


def test_photo_is_read_from_the_card_and_foreign_hosts_are_ignored() -> None:
    assert parsear_fotos(_HTML) == {
        "silvestre dangond": f"{_WEB}/wp-content/uploads/2026/01/silvestre.webp"
    }
    assert set(parsear_catalogo(_HTML)) == {"silvestre dangond", "sin foto", "foto ajena"}


def test_catalogue_serves_pages_and_photos_from_one_download() -> None:
    descargas: list[int] = []

    def descargar() -> str:
        descargas.append(1)
        return _HTML

    catalogo = CatalogoArtistas(descargar=descargar)
    assert "silvestre dangond" in catalogo.obtener()
    assert list(catalogo.obtener_fotos()) == ["silvestre dangond"]
    assert len(descargas) == 1
