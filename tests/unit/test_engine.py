from decimal import Decimal
from pathlib import Path

import pytest

from app.engine.derived import COMPUTE
from app.engine.engine import Facts, Result, evaluate, run
from app.engine.rules import AllOf, AnyOf, Comparison, Level, load_rules
from app.engine.validation import validate

SAMPLE = load_rules(Path(__file__).parent / "data" / "rules")

INTERVIEW = {
    "P1": "30",
    "P2": "normalne",
    "P9": "nie wykonano",
    "P10": "nie",
    "P11": "nie",
    "P12": "nie omówiono",
    "P13": "nie wykonano",
    "P15": "nie badano",
    "P17": "nie",
}


def consult(**changes):
    result = validate({**INTERVIEW, **changes})
    assert result.is_valid, result.errors
    return run(SAMPLE, result.values)


def fired_ids(result):
    return [rule.id for rule in result.fired]


@pytest.mark.parametrize(
    "comparison, expected",
    [
        (Comparison("P3", "=", None), True),
        (Comparison("P3", "≠", None), False),
        (Comparison("P16", "≠", True), True),
        (Comparison("P2", "in", ("normalne", "ograniczone")), True),
        (Comparison("P1", "<", Decimal(45)), True),
        (Comparison("P1", "<", Decimal(30)), False),
        (Comparison("P1", "≥", Decimal(30)), True),
        (Comparison("P1", "≥", Decimal(31)), False),
        (Comparison("P3", "<", Decimal(10)), False),
        (Comparison("P3", "≥", Decimal(10)), False),
        (Comparison("D1", "=", "brak"), True),
    ],
)
def test_comparison_semantics_including_missing_values(comparison, expected):
    values = validate(INTERVIEW).values

    assert evaluate(comparison, Facts(values)) is expected


def test_all_and_any_combine_conditions():
    values = validate(INTERVIEW).values
    true, false = Comparison("P3", "=", None), Comparison("P3", "≠", None)

    assert evaluate(AllOf((true, true)), Facts(values)) is True
    assert evaluate(AllOf((true, false)), Facts(values)) is False
    assert evaluate(AnyOf((false, true)), Facts(values)) is True
    assert evaluate(AnyOf((false, false)), Facts(values)) is False


def test_facts_compute_derived_values_once_and_on_demand():
    calls = []
    values = validate(INTERVIEW).values

    class Counting(dict):
        def __getitem__(self, key):
            calls.append(key)
            return super().__getitem__(key)

    facts = Facts(Counting(values))
    assert calls == []
    assert facts["D1"] == "brak"
    assert facts["D1"] == "brak"
    assert calls == ["P3"]


def test_interview_only_form_recommends_first_line_serology():
    result = consult()

    assert fired_ids(result) == ["G1-01"]
    assert result.derived["D1"] == "brak"


def test_high_titre_at_45_years_excludes_no_biopsy_path():
    result = consult(P1="45", P3="150", P4="10", P7="1", P8="0,7")

    assert fired_ids(result) == ["G2-07"]
    assert result.derived["D4"] is False


def test_second_sample_positive_below_ten_times_limit():
    result = consult(P3="150", P4="10", P7="1", P8="0,7", P12="tak", P5="50", P6="10")

    assert fired_ids(result) == ["G2-04"]


def test_restricted_diet_with_negative_serology_recommends_hla_first():
    result = consult(P2="ograniczone", P16="nie", P3="5", P4="10", P7="1", P8="0,7")

    assert fired_ids(result) == ["G4-04"]


def test_histology_after_challenge_without_serology_asks_for_serology():
    result = consult(
        P2="ograniczone", P16="tak", P13="1", P14_dalsza="4", P14_opuszka="1", P7="1", P8="0,7"
    )

    assert fired_ids(result) == ["G4-11"]


def test_result_lists_fired_rules_by_level():
    recommendation = consult(P1="45", P3="150", P4="10", P7="1", P8="0,7")
    information = consult(P3="150", P4="10", P7="1", P8="0,7", P12="tak", P5="50", P6="10")

    assert recommendation.at_level(Level.RECOMMENDATION) == recommendation.fired
    assert recommendation.at_level(Level.INFORMATION) == ()
    assert information.at_level(Level.INFORMATION) == information.fired
    assert information.at_level(Level.RECOMMENDATION) == ()


def test_facts_expose_parameters_and_derived_values():
    values = validate(INTERVIEW).values
    facts = Facts(values)

    assert list(facts) == list(values) + list(COMPUTE)
    assert len(facts) == len(values) + len(COMPUTE)


def test_result_contains_every_derived_value():
    result = consult()

    assert isinstance(result, Result)
    assert list(result.derived) == list(COMPUTE)
