

def test_get_seguro_rejects_a_redirect_to_an_internal_address(monkeypatch) -> None:
    """A public site bouncing the server to the cloud-metadata address must be refused."""
    from unittest.mock import MagicMock

    import pytest

    from agents.radar import url_segura

    def fake_validar(url: str) -> None:
        if "169.254" in url:
            raise url_segura.UrlNoPermitidaError("interna")

    redirect = MagicMock(is_redirect=True, headers={"location": "http://169.254.169.254/latest"})
    monkeypatch.setattr(url_segura, "validar_url_publica", fake_validar)
    monkeypatch.setattr(url_segura.requests, "get", lambda *a, **k: redirect)

    with pytest.raises(url_segura.UrlNoPermitidaError):
        url_segura.get_seguro("https://publico.example/x", timeout=5)
