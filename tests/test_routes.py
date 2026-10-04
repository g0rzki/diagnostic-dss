from sqlalchemy.exc import OperationalError

from app.extensions import db


def test_index_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200


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
