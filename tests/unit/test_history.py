import re
import shutil
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
    RESERVED_ERROR,
    SAVE_KINDS,
    Saved,
    consultation_count,
    entered_data,
    form_display,
    form_values,
    is_demo,
    label_error,
    local_time,
    normalize_label,
    parameter_values,
    review,
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


@pytest.mark.parametrize("label", ["PRZYKŁAD-1", "przykład 2", " Przyklad-9", "PRZYKLAD"])
def test_labels_starting_with_przyklad_are_reserved_for_demo_cases(label):
    assert is_demo(label)
    assert label_error(" ".join(label.split()).upper()) == RESERVED_ERROR


@pytest.mark.parametrize("label", ["P-001", "XPRZYKŁAD", "PRZYKŁ", "KONTROLA 3"])
def test_other_labels_are_not_demo(label):
    assert not is_demo(label)


@pytest.mark.parametrize("kind", SAVE_KINDS)
def test_save_kind_gives_back_the_same_message(kind):
    saved = Saved.from_kind("P-001", 2, kind)

    assert saved.kind == kind
    assert saved.message == Saved("P-001", 2, saved.created, saved.new_case).message


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


def test_entered_data_lists_every_given_value_in_register_order():
    values = validate({**CATALOG["defaults"], "P1": "30", **SEROLOGY}).values

    entered = entered_data(values)

    assert [item.field for item in entered][:5] == ["P1", "P2", "P3", "P4", "P7"]
    assert ("P7", "1,5 g/L") in [(item.field, item.after) for item in entered]
    assert all(item.before is None for item in entered)


def changed_base(tmp_path, change):
    rules = tmp_path / "rules"
    shutil.copytree(Config.RULES_DIR, rules)
    g2 = rules / "g2.yaml"
    g2.write_text(change(g2.read_text(encoding="utf-8")), encoding="utf-8")
    return load_rules(rules)


def test_review_of_consultation_with_current_rules_is_consistent():
    record = review(consultation(2, SEROLOGY), BASE)

    assert record.same_version and record.same_result
    assert [rule.id for rule in record.result.fired] == ["G2-01"]
    assert record.current == ("G2-01",)
    assert record.added == record.removed == record.missing == ()
    assert record.values["P7"] == validate({**CATALOG["defaults"], **SEROLOGY}).values["P7"]


def test_review_after_change_without_effect_reports_new_version_and_same_result(tmp_path):
    base = changed_base(tmp_path, lambda text: text + "\n# uwaga bez wpływu na wynik\n")

    record = review(consultation(2, SEROLOGY), base)

    assert not record.same_version
    assert record.same_result
    assert record.current_version == base.version != record.stored_version


def test_review_after_changed_condition_lists_rules_added_and_removed(tmp_path):
    base = changed_base(
        tmp_path, lambda text: text.replace("[P12, '=', nie omówiono]", "[P12, '=', tak]")
    )

    before = review(consultation(2, SEROLOGY), base)
    agreed = review(consultation(9, {**SEROLOGY, "P12": "tak"}), base)

    assert (before.added, before.removed, before.missing) == ((), ("G2-01",), ())
    assert [rule.id for rule in before.result.fired] == ["G2-01"]
    assert (agreed.added, agreed.removed) == (("G2-01",), ())


def test_review_marks_stored_rule_missing_from_current_base(tmp_path):
    rule = re.compile(r"  - id: G2-01\n.*?(?=  - id: )", re.S)
    base = changed_base(tmp_path, lambda text: rule.sub("", text))

    record = review(consultation(2, SEROLOGY), base)

    assert record.missing == ("G2-01",)
    assert record.removed == ("G2-01",)
    assert record.result.fired == ()
