import pytest

from app.config import Config
from app.engine.engine import run
from app.engine.rules import load_rules
from app.engine.validation import validate
from app.scenarios import BY_SLUG, SCENARIOS, matching_scenario

BASE = load_rules(Config.RULES_DIR)
VARIANTS = [(scenario, variant) for scenario in SCENARIOS for variant in scenario.variants]


def fired(values):
    validation = validate(values)
    assert validation.is_valid, validation.errors
    assert validation.warnings == ()
    return tuple(rule.id for rule in run(BASE, validation.values).fired)


def test_there_are_four_scenarios_with_unique_slugs():
    assert len(SCENARIOS) == 4
    assert len(BY_SLUG) == 4


def test_scenarios_cover_every_rule_group():
    groups = {code[:2] for scenario in SCENARIOS for code in scenario.expected}

    assert groups == {"G1", "G2", "G3", "G4"}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.slug)
def test_scenario_gives_its_expected_result(scenario):
    assert sorted(fired(scenario.values)) == sorted(scenario.expected)


@pytest.mark.parametrize(
    ("scenario", "variant"), VARIANTS, ids=[f"{s.slug}: {v.change}" for s, v in VARIANTS]
)
def test_scenario_variant_gives_its_expected_result(scenario, variant):
    assert sorted(fired({**scenario.values, **variant.values})) == sorted(variant.expected)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.slug)
def test_scenario_is_recognised_from_submitted_form_with_empty_fields(scenario):
    form = {"P5": "", "P14_dalsza": "", **scenario.values}

    assert matching_scenario(form) == scenario


def test_changed_data_no_longer_match_the_scenario():
    scenario = BY_SLUG["bez-biopsji"]

    assert matching_scenario({**scenario.values, "P5": "8"}) is None
    assert matching_scenario({**scenario.values, "P17": "tak"}) is None
