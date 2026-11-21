import pytest
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()


@pytest.fixture
def app():
    from app import create_app
    from app.config import TestConfig

    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def database(app):
    from app.extensions import db

    def empty_tables():
        db.session.rollback()
        db.session.execute(text("TRUNCATE consultations, cases RESTART IDENTITY"))
        db.session.commit()

    with app.app_context():
        empty_tables()
        yield db
        empty_tables()
