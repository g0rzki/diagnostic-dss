import pytest

from app.config import Config
from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS
from app.engine.rules import load_rules
from app.glossary import (
    DEFINITIONS,
    GROUPS,
    derived_entries,
    parameter_entries,
    parameter_tips,
    ptge_text,
    required_text,
    rules_phrase,
    source_entries,
    source_text,
    value_text,
)


@pytest.fixture(scope="module")
def base():
    return load_rules(Config.RULES_DIR)


def test_every_derived_value_has_a_definition():
    assert set(DEFINITIONS) == set(DERIVED)


def test_every_rule_group_has_a_name(base):
    assert {rule.group for rule in base.rules} == set(GROUPS)


@pytest.mark.parametrize(
    ("param", "expected"),
    [
        ("P1", "liczba całkowita 18–120 [lata]"),
        ("P3", "liczba > 0"),
        ("P7", "liczba ≥ 0 [g/L]"),
        ("P8", "liczba > 0,07 [g/L]"),
        ("P13", "nie wykonano / 0 / 1 / 2 / 3"),
        ("P14", "dwie liczby całkowite ≥ 0 (dalsza, opuszka)"),
        ("P17", "tak / nie"),
    ],
)
def test_value_text(param, expected):
    assert value_text(PARAMETERS[param]) == expected


@pytest.mark.parametrize(
    ("param", "expected"),
    [
        ("P1", "tak"),
        ("P3", "nie (brak wyniku jest dopuszczalny)"),
        ("P4", "gdy podano P3"),
        ("P14", "gdy P13 ≠ nie wykonano"),
        ("P16", "gdy P2 = ograniczone"),
    ],
)
def test_required_text(param, expected):
    assert required_text(PARAMETERS[param]) == expected


def test_rules_phrase_agrees_with_number():
    assert rules_phrase(1) == "1 reguły"
    assert rules_phrase(2) == "2 reguł"


def test_parameter_rules_follow_uses(base):
    entries = {entry.param.id: entry for entry in parameter_entries(base)}

    assert entries["P10"].rules == ("G4-02",)
    assert entries["P17"].rules == ("G1-06",)
    assert all(entry.rules for entry in entries.values())


def test_derived_rules_read_the_value_directly(base):
    entries = {entry.id: entry for entry in derived_entries(base)}

    assert entries["D7"].rules == ("G3-13", "G3-17")
    assert entries["D2_2"].rules == ("G2-04",)
    assert all(entry.rules for entry in entries.values())


def test_tip_describes_parameter(base):
    tip = parameter_tips(base)["P4"]

    assert tip.startswith("Dana wejściowa P4: GGN laboratorium dla wyniku 1.")
    assert "Wymagana: gdy podano P3." in tip


def rule(base, rule_id):
    return next(rule for rule in base.rules if rule.id == rule_id)


@pytest.mark.parametrize(
    ("rule_id", "expected"),
    [
        ("G1-01", "ESsCD 2025 cz. 1, s. 1865"),
        ("G1-02", "ESsCD 2025 cz. 1, s. 1865, 1866, 1875"),
        ("G3-09", "ESsCD 2025 cz. 1, s. 1868, 1872, 1875"),
        ("G4-07", "ESsCD 2025 cz. 1, s. 1876–1877"),
    ],
)
def test_source_text_lists_pages(base, rule_id, expected):
    assert source_text(base, rule(base, rule_id)) == expected


@pytest.mark.parametrize(
    ("rule_id", "expected"),
    [
        ("G1-01", "zgodność, s. 5"),
        ("G2-10", "brak odniesienia"),
        ("G3-03", "różnica, s. 5, 7; kierunek reguły według PTG-E"),
    ],
)
def test_ptge_text(base, rule_id, expected):
    assert ptge_text(rule(base, rule_id)) == expected


def test_every_source_has_role_and_doi(base):
    entries = source_entries(base)

    assert [entry.name for entry in entries] == ["ESsCD 2025 cz. 1", "PTG-E 2026"]
    assert [entry.doi for entry in entries] == ["10.1002/ueg2.70119", "10.5114/pg.2026.164973"]
    assert all(entry.role and not entry.citation.endswith("doi:") for entry in entries)
