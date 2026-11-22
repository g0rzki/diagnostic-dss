from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from app.config import Config
from app.engine.engine import evaluate, run
from app.engine.parameters import PARAMETERS
from app.engine.rules import Grade, load_rules
from app.engine.validation import validate
from app.explanation import condition_fields, explain, grade_text, value_text

BASE = load_rules(Config.RULES_DIR)
RULES = {rule.id: rule for rule in BASE.rules}
CATALOG = yaml.safe_load(
    (Path(__file__).parent / "data" / "catalog_cases.yaml").read_text(encoding="utf-8")
)
FIRING = [case for case in CATALOG["cases"] if case["fires"]]


def consultation(**data):
    validation = validate({**CATALOG["defaults"], **data})
    assert validation.is_valid, validation.errors
    result = run(BASE, validation.values)
    return validation.values, result


def empty(**values):
    return {**dict.fromkeys(PARAMETERS), **values}


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("P1", 30, "30 lat"),
        ("P1", 22, "22 lata"),
        ("P1", 44, "44 lata"),
        ("P1", 112, "112 lat"),
        ("P3", Decimal("150"), "150"),
        ("P3", Decimal("12.5"), "12,5"),
        ("P7", Decimal("1.5"), "1,5 g/L"),
        ("P10", True, "tak"),
        ("P11", False, "nie"),
        ("P13", "2", "2"),
        ("P14", (4, 1), "część dalsza 4, opuszka 1"),
        ("P3", None, "brak wyniku"),
    ],
)
def test_value_text(field, value, expected):
    assert value_text(field, empty(**{field: value})) == expected


def test_value_text_marks_fields_that_do_not_apply():
    assert value_text("P16", empty(P2="normalne")) == "nie dotyczy"
    assert value_text("P4", empty()) == "nie dotyczy"
    assert value_text("P16", empty(P2="ograniczone")) == "brak wyniku"


def test_value_text_for_derived_values():
    assert value_text("D4", {"D4": True}) == "tak"
    assert value_text("D1", {"D1": "dodatni"}) == "dodatni"


def test_condition_fields_keep_order_without_repeats():
    assert condition_fields(RULES["G2-01"].condition) == ("D4", "P12", "D1_2")


@pytest.mark.parametrize(
    ("grade", "expected"),
    [
        (
            Grade("wysoka", "silne", 100),
            "pewność dowodów: wysoka, siła zalecenia: silne, zgoda 100%",
        ),
        (
            Grade("nie dotyczy", "dobra praktyka (UGPS)", 95),
            "siła zalecenia: dobra praktyka (UGPS), zgoda 95%",
        ),
        (Grade("wysoka", "silne", None), "pewność dowodów: wysoka, siła zalecenia: silne"),
    ],
)
def test_grade_text(grade, expected):
    assert grade_text(grade) == expected


def test_explanation_of_no_biopsy_path():
    values, result = consultation(P3=150, P4=10, P7=1.5, P8=0.7)
    why = explain(BASE, RULES["G2-01"], values, result.derived)

    assert [(fact.id, fact.text) for fact in why.facts] == [
        ("D4", "tak"),
        ("P12", "nie omówiono"),
        ("D1_2", "brak"),
    ]
    assert [fact.id for fact in why.inputs] == [
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P7",
        "P11",
        "P13",
        "P15",
    ]
    assert why.source == (
        "ESsCD 2025 cz. 1: Q.IV.1.2, kluczowe uwagi (s. 1870) i uzasadnienie (s. 1871)"
    )
    assert why.evidence == "Zalecenie; siła zalecenia: dobra praktyka (UGPS), zgoda 95%"
    assert why.ptge == "zgodność, s. 7"
    assert ("D4", True) in why.condition_parts


def test_explanation_shows_ptge_direction_and_missing_grade():
    values, result = consultation(
        P3=25, P4=10, P7=1.5, P8=0.7, P13="2", P14_dalsza=4, P14_opuszka=1
    )
    why = explain(BASE, RULES["G3-07"], values, result.derived)

    assert why.evidence == "Uzasadnienie (bez przypisanej oceny GRADE)"
    assert why.ptge == "różnica, s. 8; kierunek reguły według PTG-E"


def test_explanation_adds_ptge_grade():
    values, result = consultation(P17=True)
    why = explain(BASE, RULES["G1-01"], values, result.derived)

    assert why.ptge == "zgodność, s. 5; pewność dowodów: wysoka, siła zalecenia: silne"


def test_source_without_page_in_location_gets_the_page():
    rule = next(rule for rule in BASE.rules if "s. " not in rule.source.location)
    values, result = consultation()
    why = explain(BASE, rule, values, result.derived)

    assert why.source.endswith(f", s. {rule.source.page}")


@pytest.mark.parametrize(
    "case", FIRING, ids=[f"{case['rule']}-{index}" for index, case in enumerate(FIRING)]
)
def test_every_fired_rule_is_explained_by_the_values_it_shows(case):
    values, result = consultation(**case["input"])

    for rule in result.fired:
        why = explain(BASE, rule, values, result.derived)
        shown = {fact.id: fact.value for fact in why.facts}

        assert tuple(shown) == condition_fields(rule.condition)
        assert evaluate(rule.condition, shown)
        assert {fact.id for fact in why.inputs} <= set(rule.uses) - set(shown)
        assert all(fact.text for fact in why.facts + why.inputs)
        assert why.source and why.evidence and why.ptge
