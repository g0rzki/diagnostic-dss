import os

from sqlalchemy import URL


def database_url(database):
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "dss"),
        password=os.environ.get("POSTGRES_PASSWORD", "dss"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=database,
    )


class Config:
    SQLALCHEMY_DATABASE_URI = database_url(os.environ.get("POSTGRES_DB", "dss"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = database_url("dss_test")
