import os

from sqlalchemy import URL


class Config:
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "dss"),
        password=os.environ.get("POSTGRES_PASSWORD", "dss"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "dss"),
    )
