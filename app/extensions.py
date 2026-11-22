from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}

# Numer blokady doradczej PostgreSQL na czas zmian bazy przy starcie aplikacji (migracja,
# przypadki pokazowe), wspólny dla wszystkich procesów aplikacji.
MIGRATION_LOCK = 1

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))
migrate = Migrate(render_as_batch=False)
