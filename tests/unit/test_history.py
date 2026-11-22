import zoneinfo
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from app.config import Config
from app.engine.engine import run
from app.engine.rules import load_rules
from app.engine.validation import validate
from app.history import (
    LABEL_ERROR,
    consultation_count,
    form_display,
    form_values,
    label_error,
    local_time,
    normalize_label,
    parameter_values,
    timeline,
)
from app.models import Case, Consultation
from app.scenarios import SCENARIOS

BASE = load_rules(Config.RULES_DIR)
CATALOG = yaml.safe_load(
    (Path(__file__).parent / "data" / "catalog_cases.yaml").read_text(encoding="utf-8")
)
CATALOG_INPUTS = [{**CATALOG["defaults"], **case["input"]} for case in CATALOG["cases"]]
SCENARIO_INPUTS = [scenario.values for scenario in SCENARIOS] + [
    {**scenario.values, **variant.values} for scenario in SCENARIOS for variant in scenario.variants
]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("P-001", "P-001"),
        ("  p-001 ", "P-001"),
        ("pacjent  12\tb", "PACJENT 12 B"),
        ("", ""),
        (None, ""),
    ],
)
def test_label_is_trimmed_collapsed_and_upper_cased(raw, expected):
    assert normalize_label(raw) == expected


@pytest.mark.parametrize("label", ["P-001", "A", "2026.11_ŁÓDŹ", "X" * 30, "KONTROLA 3"])
def test_valid_labels_are_accepted(label):
    assert label_error(label) is None


@pytest.mark.parametrize("label", ["-P1", "_P1", ".", "..", "P/001", "P#1", "X" * 31])
def test_invalid_labels_are_rejected(label):
    assert label_error(label) == LABEL_ERROR


@pytest.mark.parametrize("raw", CATALOG_INPUTS + SCENARIO_INPUTS)
def test_stored_form_values_give_back_the_same_validated_values(raw):
    values = validate(raw).values

    stored = form_values(values)

    assert parameter_values(stored) == values
    assert form_values(parameter_values(stored)) == stored
    assert parameter_values(form_display(stored)) == values


def test_stored_form_values_are_canonical_text():
    raw = {"P1": "30", "P3": "< 1,50", "P4": "10", "P7": "0,70", "P8": "0,7", "P13": "3"}
    raw |= {"P14_dalsza": "4", "P14_opuszka": "1"}
    values = validate({**CATALOG["defaults"], **raw}).values

    stored = form_values(values)

    assert stored["P3"] == "1.5"
    assert stored["P7"] == "0.7"
    assert (stored["P14_dalsza"], stored["P14_opuszka"]) == ("4", "1")
    assert stored["P10"] == "nie"
    assert stored["P5"] == stored["P16"] == ""
    assert "P14" not in stored


def test_form_display_writes_decimals_with_comma_and_leaves_other_fields():
    raw = {"P1": "30", "P3": "150", "P4": "10", "P7": "1,5", "P8": "0,7", "P13": "3"}
    raw |= {"P14_dalsza": "4", "P14_opuszka": "1"}
    stored = form_values(validate({**CATALOG["defaults"], **raw}).values)

    shown = form_display(stored)

    assert (shown["P7"], shown["P8"], shown["P3"]) == ("1,5", "0,7", "150")
    assert {name: value for name, value in shown.items() if name not in ("P7", "P8")} == {
        name: value for name, value in stored.items() if name not in ("P7", "P8")
    }


@pytest.mark.parametrize(
    "number, text",
    [
        (1, "1 konsultacja"),
        (2, "2 konsultacje"),
        (4, "4 konsultacje"),
        (5, "5 konsultacji"),
        (12, "12 konsultacji"),
        (22, "22 konsultacje"),
        (25, "25 konsultacji"),
    ],
)
def test_consultation_count_uses_polish_plural(number, text):
    assert consultation_count(number) == text


def test_local_time_is_shown_in_polish_time_zone_also_in_summer():
    assert local_time(datetime(2026, 11, 2, 8, 0, tzinfo=UTC)) == "02.11.2026, 09:00"
    assert local_time(datetime(2026, 7, 1, 8, 0, tzinfo=UTC)) == "01.07.2026, 10:00"


def test_polish_time_zone_is_available_without_system_time_zone_data():
    zoneinfo.reset_tzpath(to=[])
    try:
        zone = zoneinfo.ZoneInfo.no_cache("Europe/Warsaw")
    finally:
        zoneinfo.reset_tzpath()

    assert zone.utcoffset(datetime(2026, 7, 1)) == timedelta(hours=2)


def consultation(day, raw):
    values = validate({**CATALOG["defaults"], "P1": "30", **raw}).values
    result = run(BASE, values)
    return Consultation(
        created_at=datetime(2026, 11, day, 9, 0, tzinfo=UTC),
        parameters=form_values(values),
        derived=dict(result.derived),
        fired_rules=[rule.id for rule in result.fired],
        rules_version=BASE.version,
    )


SEROLOGY = {"P3": "150", "P4": "10", "P7": "1,5", "P8": "0,7"}


def test_timeline_lists_entered_data_then_changes_and_rule_differences():
    case = Case(
        label="P-001",
        consultations=[
            consultation(2, {}),
            consultation(9, SEROLOGY),
            consultation(16, {**SEROLOGY, "P12": "tak"}),
        ],
    )

    first, second, third = timeline(case, BASE)

    assert [change.field for change in first.changes] == [
        "P1",
        "P2",
        "P9",
        "P10",
        "P11",
        "P12",
        "P13",
        "P15",
        "P17",
    ]
    assert all(change.before is None for change in first.changes)
    assert (first.fired, first.added, first.removed) == (("G1-01",), (), ())
    assert [(c.field, c.before, c.after) for c in second.changes] == [
        ("P3", "brak wyniku", "150"),
        ("P4", "nie dotyczy", "10"),
        ("P7", "brak wyniku", "1,5 g/L"),
        ("P8", "nie dotyczy", "0,7 g/L"),
    ]
    assert (second.added, second.removed) == (("G2-01",), ("G1-01",))
    assert [(c.field, c.before, c.after) for c in third.changes] == [("P12", "nie omówiono", "tak")]
    assert third.recommendations == ("G2-02",)
    assert [entry.number for entry in (first, second, third)] == [1, 2, 3]


def test_timeline_marks_change_of_rule_base_version():
    earlier = consultation(2, SEROLOGY)
    earlier.rules_version = "0" * 64
    later = consultation(9, SEROLOGY)
    case = Case(label="P-002", consultations=[earlier, later])

    first, second = timeline(case, BASE)

    assert first.previous_version is None
    assert second.previous_version == "0" * 64
    assert second.changes == ()
