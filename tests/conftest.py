import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def app():
    from app import create_app
    from app.config import TestConfig

    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()
