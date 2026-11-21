import logging
import threading
from datetime import UTC, datetime, timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import MIGRATION_LOCK, create_app, upgrade_database
from app.config import TestConfig
from app.extensions import db
from app.models import Case, Consultation

TABLES = {"alembic_version", "cases", "consultations"}


def table_names():
    return set(inspect(db.engine).get_table_names())


def current_revision():
    with db.engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def head_revision(app):
    return ScriptDirectory(str(app.config["MIGRATIONS_DIR"])).get_current_head()


def drop_tables():
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS consultations, cases, alembic_version"))


def consultation(**changes):
    fields = {
        "parameters": {"P1": "30"},
        "derived": {"D4": False},
        "fired_rules": ["G1-01"],
        "rules_version": "0" * 64,
    }
    return Consultation(**{**fields, **changes})


def test_application_start_creates_schema_on_empty_database(app):
    with app.app_context():
        drop_tables()
        assert not TABLES & table_names()

    with create_app(TestConfig).app_context():
        assert TABLES <= table_names()
        assert current_revision() == head_revision(app)


def test_application_restart_keeps_saved_data(database):
    database.session.add(Case(label="P-001"))
    database.session.commit()

    create_app(TestConfig)

    assert database.session.scalars(select(Case.label)).all() == ["P-001"]


def test_downgrade_removes_tables_and_upgrade_restores_them(app):
    with app.app_context():
        downgrade(revision="base")
        assert not {"cases", "consultations"} & table_names()
        assert current_revision() is None

        upgrade()

        assert TABLES <= table_names()
        assert current_revision() == head_revision(app)


def test_models_match_latest_migration(app):
    with app.app_context(), db.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []


def test_migration_on_start_waits_while_another_process_migrates(app):
    errors = []

    def start():
        try:
            with app.app_context():
                upgrade_database()
        except Exception as error:
            errors.append(error)

    with app.app_context():
        drop_tables()
        thread = threading.Thread(target=start, daemon=True)
        with db.engine.connect() as other_process:
            other_process.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            try:
                thread.start()
                thread.join(timeout=0.5)
                waiting = thread.is_alive()
                created_while_locked = TABLES & table_names()
            finally:
                other_process.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK}
                )
        thread.join(timeout=10)

        assert waiting
        assert not created_while_locked
        assert not thread.is_alive()
        assert errors == []
        assert TABLES <= table_names()


def test_migration_on_start_keeps_existing_loggers_enabled():
    access_log = logging.getLogger("gunicorn.access")

    create_app(TestConfig)

    assert not access_log.disabled


def test_consultation_is_saved_without_changes(database):
    saved = consultation(
        parameters={"P1": "30", "P3": "<1", "P14": [4, 1], "P16": None},
        derived={"D2": False, "D3": "norma"},
        fired_rules=["G2-04", "G2-07", "G2-10"],
        rules_version="a" * 64,
    )
    database.session.add(Case(label="P-001", consultations=[saved]))
    database.session.commit()
    database.session.expire_all()

    loaded = database.session.get(Consultation, saved.id)

    assert loaded.parameters == {"P1": "30", "P3": "<1", "P14": [4, 1], "P16": None}
    assert loaded.derived == {"D2": False, "D3": "norma"}
    assert loaded.fired_rules == ["G2-04", "G2-07", "G2-10"]
    assert loaded.rules_version == "a" * 64
    assert loaded.created_at.tzinfo is not None
    assert loaded.case.label == "P-001"


def test_consultations_of_case_are_ordered_by_time(database):
    start = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    case = Case(label="P-001")
    for days, fired in ((14, ["G2-01"]), (0, ["G1-01"]), (28, ["G2-02"])):
        case.consultations.append(
            consultation(created_at=start + timedelta(days=days), fired_rules=fired)
        )
    database.session.add(case)
    database.session.commit()
    database.session.expire_all()

    loaded = database.session.scalars(select(Case)).one()

    assert [item.fired_rules for item in loaded.consultations] == [
        ["G1-01"],
        ["G2-01"],
        ["G2-02"],
    ]


def test_case_label_is_unique(database):
    database.session.add_all([Case(label="P-001"), Case(label="P-001")])

    with pytest.raises(IntegrityError):
        database.session.commit()


def test_consultation_must_belong_to_existing_case(database):
    database.session.add(consultation(case_id=999))

    with pytest.raises(IntegrityError):
        database.session.commit()
