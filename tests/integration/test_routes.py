import pytest
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.scenarios import BY_SLUG


def test_index_renders_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "System wspomagania decyzji diagnostycznych" in response.get_data(as_text=True)


def test_index_describes_prototype_status(client):
    page = client.get("/").get_data(as_text=True)

    assert "System nie przeszedł walidacji klinicznej" in page


def test_index_describes_domain_and_sources(client):
    page = client.get("/").get_data(as_text=True)

    assert "Celiakia" in page
    assert "ESsCD 2025" in page
    assert "PTG-E 2026" in page
    assert 'href="/konsultacja"' in page
    assert 'href="/slownik"' in page


@pytest.mark.parametrize("url", ["/", "/konsultacja", "/slownik", "/nie-ma"])
def test_every_page_shows_prototype_notice_in_footer(client, url):
    page = client.get(url).get_data(as_text=True)

    assert "Prototyp badawczy pracy inżynierskiej, bez walidacji klinicznej." in page


def test_health_returns_200_when_database_available(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_unavailable(client, monkeypatch):
    def failing_execute(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(db.session, "execute", failing_execute)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}


def test_rule_codes_are_not_set_in_monospace_font(client):
    result = client.post("/konsultacja", data=BY_SLUG["bez-biopsji"].values).get_data(as_text=True)
    glossary = client.get("/slownik").get_data(as_text=True)

    assert 'href="/slownik#G2-03"' in result
    assert 'href="#G2-03"' in glossary
    assert "font-mono" not in result
    assert "font-mono" not in glossary


def test_pages_link_favicon(client):
    page = client.get("/").get_data(as_text=True)

    assert '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">' in page
    assert client.get("/static/favicon.svg").status_code == 200


@pytest.mark.parametrize("url", ["/nie-ma", "/historia/BRAK", "/konsultacja?przyklad=brak"])
def test_missing_page_shows_polish_error_page(client, database, url):
    response = client.get(url)
    page = response.get_data(as_text=True)

    assert response.status_code == 404
    assert response.content_type == "text/html; charset=utf-8"
    assert '<html lang="pl">' in page
    assert "<title>Nie znaleziono strony | Diagnostic DSS</title>" in page
    assert "Błąd 404" in page
    assert "Not Found" not in page
    assert 'href="/" class="btn-primary"' in page
    assert 'href="/konsultacja" class="btn-secondary"' in page


def test_form_only_address_opened_directly_shows_polish_error_page(client):
    response = client.get("/konsultacja/popraw")
    page = response.get_data(as_text=True)

    assert response.status_code == 405
    assert set(response.headers["Allow"].split(", ")) == {"OPTIONS", "POST"}
    assert "<title>Niedozwolona metoda zapytania | Diagnostic DSS</title>" in page
    assert "Ten adres przyjmuje tylko dane wysłane z formularza konsultacji." in page
    assert "Method Not Allowed" not in page


def test_unexpected_error_shows_polish_error_page_without_details(app, client, monkeypatch):
    def failing_summaries(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))

    app.config["PROPAGATE_EXCEPTIONS"] = False
    monkeypatch.setattr("app.routes.summaries", failing_summaries)

    response = client.get("/historia")
    page = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "<title>Błąd serwera | Diagnostic DSS</title>" in page
    assert "Spróbuj ponownie za chwilę." in page
    assert "connection refused" not in page
    assert "Internal Server Error" not in page
