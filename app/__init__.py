from flask import Flask
from flask_migrate import upgrade
from sqlalchemy import text

# Import rejestruje tabele w metadanych, z których korzystają migracje.
from app import models  # noqa: F401
from app.config import Config
from app.demo import insert_demo_cases
from app.engine.rules import load_rules
from app.extensions import MIGRATION_LOCK, db, migrate
from app.routes import bp


def upgrade_database():
    with db.engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK})
        upgrade()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config["MIGRATIONS_DIR"])
    app.extensions["rule_base"] = load_rules(app.config["RULES_DIR"])
    with app.app_context():
        upgrade_database()
        if app.config["DEMO_CASES"]:
            insert_demo_cases(app.extensions["rule_base"])
    app.register_blueprint(bp)
    return app
