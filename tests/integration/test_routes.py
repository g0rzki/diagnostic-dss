import pytest
from sqlalchemy.exc import OperationalError

from app.extensions import db


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


@pytest.mark.parametrize("url", ["/", "/konsultacja", "/slownik"])
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
