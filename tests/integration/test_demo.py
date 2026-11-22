import re
import threading

import pytest
from sqlalchemy import delete, select, text

from app import create_app
from app.config import TestConfig
from app.demo import DEMO_CASES, insert_demo_cases
from app.extensions import MIGRATION_LOCK, db
from app.forms import INTERVIEW_DEFAULTS
from app.models import Case, Consultation


class DemoConfig(TestConfig):
    DEMO_CASES = True


@pytest.fixture
def demo_app(database):
    return create_app(DemoConfig)


def demo_cases():
    return db.session.scalars(select(Case).where(Case.label.like("PRZYKŁAD%"))).all()


def test_start_inserts_demo_cases_with_results_of_current_rules(demo_app):
    base = demo_app.extensions["rule_base"]

    cases = {case.label: case for case in demo_cases()}

    assert sorted(cases) == [demo.label for demo in DEMO_CASES]
    assert [len(cases[demo.label].consultations) for demo in DEMO_CASES] == [4, 4, 3, 4]
    versions = {item.rules_version for case in cases.values() for item in case.consultations}
    assert versions == {base.version}
    assert cases["PRZYKŁAD-1"].consultations[-1].fired_rules == ["G2-03"]
    assert cases["PRZYKŁAD-1"].created_at == cases["PRZYKŁAD-1"].consultations[0].created_at


def test_restart_does_not_duplicate_demo_cases_and_restores_missing_one(demo_app):
    removed = db.session.scalars(select(Case).where(Case.label == "PRZYKŁAD-2")).one()
    db.session.execute(delete(Consultation).where(Consultation.case_id == removed.id))
    db.session.delete(removed)
    db.session.commit()

    create_app(DemoConfig)
    create_app(DemoConfig)

    assert sorted(case.label for case in demo_cases()) == [demo.label for demo in DEMO_CASES]
    assert len(db.session.scalars(select(Consultation)).all()) == 15


def test_demo_insert_waits_while_another_process_holds_the_lock(database, app):
    errors = []

    def start():
        try:
            with app.app_context():
                insert_demo_cases(app.extensions["rule_base"])
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=start, daemon=True)
    with db.engine.connect() as other_process:
        other_process.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
        try:
            thread.start()
            thread.join(timeout=0.5)
            waiting = thread.is_alive()
            inserted_while_locked = db.session.scalars(select(Case.label)).all()
        finally:
            other_process.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
    thread.join(timeout=10)

    assert waiting
    assert inserted_while_locked == []
    assert errors == []
    assert len(demo_cases()) == len(DEMO_CASES)


def test_history_shows_demo_cases_first_in_separate_section(demo_app):
    client = demo_app.test_client()
    client.post("/konsultacja", data={**INTERVIEW_DEFAULTS, "P1": "30", "oznaczenie": "P-001"})

    page = client.get("/historia").get_data(as_text=True)

    demo, saved = page.split("Przypadki zapisane w formularzu")
    positions = [demo.index(item.label) for item in DEMO_CASES]
    assert demo.index("Przypadki pokazowe") < positions[0]
    assert positions == sorted(positions)
    assert "P-001" in saved
    assert "PRZYKŁAD" not in saved
    duplicates = re.findall(r'id="([^"]+)"', page)
    assert len(duplicates) == len(set(duplicates))


def test_demo_case_is_read_only(demo_app):
    client = demo_app.test_client()
    case_page = client.get("/historia/PRZYKŁAD-1").get_data(as_text=True)
    form_page = client.get("/konsultacja?przypadek=przykład-1").get_data(as_text=True)
    saved_page = client.get("/historia/PRZYKŁAD-1/2").get_data(as_text=True)

    assert "Otwórz dane w formularzu" in case_page
    assert "Kontynuuj diagnostykę" not in case_page
    assert 'id="oznaczenie" name="oznaczenie" value=""' in form_page
    assert 'value="120"' in form_page
    assert 'name="oznaczenie"' not in saved_page
    assert "Przypadek pokazowy jest tylko do odczytu." in saved_page


def test_demo_case_cannot_be_extended_through_the_form(demo_app):
    client = demo_app.test_client()
    data = {**INTERVIEW_DEFAULTS, "P1": "34", "oznaczenie": "PRZYKŁAD-1"}

    response = client.post("/konsultacja", data=data)

    assert response.status_code == 422
    assert len(db.session.scalars(select(Consultation)).all()) == 15
