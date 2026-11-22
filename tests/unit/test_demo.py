from datetime import UTC, datetime

import pytest

from app.config import Config
from app.demo import DEMO_CASES, DemoCase, Stage, demo_consultations
from app.engine.rules import load_rules
from app.history import LABEL, LOCAL_TIME, is_demo

BASE = load_rules(Config.RULES_DIR)
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)

EXPECTED = {
    "PRZYKŁAD-1": [["G1-01"], ["G2-01"], ["G2-02"], ["G2-03"]],
    "PRZYKŁAD-2": [["G2-01"], ["G2-02"], ["G2-05", "G3-03"], ["G3-05"]],
    "PRZYKŁAD-3": [["G1-01"], ["G1-03"], ["G3-03", "G4-01"]],
    "PRZYKŁAD-4": [["G1-02", "G4-04"], ["G1-02", "G4-06"], ["G3-03", "G4-08"], ["G3-05"]],
}


def test_every_demo_case_is_checked():
    assert [demo.label for demo in DEMO_CASES] == list(EXPECTED)


@pytest.mark.parametrize("demo", DEMO_CASES, ids=lambda demo: demo.label)
def test_demo_case_follows_expected_diagnostic_path(demo):
    consultations = demo_consultations(demo, BASE, NOW)

    assert [consultation.fired_rules for consultation in consultations] == EXPECTED[demo.label]
    assert {consultation.rules_version for consultation in consultations} == {BASE.version}


@pytest.mark.parametrize("demo", DEMO_CASES, ids=lambda demo: demo.label)
def test_demo_case_has_valid_reserved_label_and_visits_in_the_past_in_order(demo):
    dates = [consultation.created_at for consultation in demo_consultations(demo, BASE, NOW)]

    assert LABEL.fullmatch(demo.label) and is_demo(demo.label)
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)
    assert dates[-1] < NOW
    assert all(8 <= date.astimezone(LOCAL_TIME).hour < 16 for date in dates)


def test_demo_cases_have_different_last_visits():
    last = [demo_consultations(demo, BASE, NOW)[-1].created_at for demo in DEMO_CASES]

    assert len(set(last)) == len(last)


def test_demo_case_with_invalid_data_is_rejected():
    broken = DemoCase("PRZYKŁAD-9", (Stage(10, "09:00", {"P1": "abc"}),))

    with pytest.raises(ValueError, match="PRZYKŁAD-9"):
        demo_consultations(broken, BASE, NOW)
