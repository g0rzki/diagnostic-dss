from collections import Counter, defaultdict
from pathlib import Path

import pytest
import yaml

from app.config import Config
from app.engine.derived import DERIVED
from app.engine.engine import run
from app.engine.parameters import PARAMETERS
from app.engine.rules import AllOf, AnyOf, Comparison, load_rules
from app.engine.validation import validate

BASE = load_rules(Config.RULES_DIR)
CATALOG = yaml.safe_load(
    (Path(__file__).parent / "data" / "catalog_cases.yaml").read_text(encoding="utf-8")
)
CASES = CATALOG["cases"]


def case_id(case):
    return f"{case['rule']}-{'fires' if case['fires'] else 'silent'}"


def fields(node):
    if isinstance(node, Comparison):
        return {node.field}
    assert isinstance(node, AllOf | AnyOf)
    return set().union(*(fields(child) for child in node.conditions))


def test_rule_base_contains_all_45_rules_in_four_groups():
    groups = Counter(rule.group for rule in BASE.rules)

    assert groups == {"G1": 7, "G2": 10, "G3": 17, "G4": 11}


def test_every_rule_has_catalog_cases_where_it_fires_and_where_it_does_not():
    outcomes = defaultdict(set)
    for case in CASES:
        outcomes[case["rule"]].add(case["fires"])

    assert set(outcomes) == {rule.id for rule in BASE.rules}
    assert all(found == {True, False} for found in outcomes.values())


def test_every_parameter_and_derived_value_is_used_by_some_rule():
    used = set().union(*(fields(rule.condition) for rule in BASE.rules))
    declared = set().union(*(rule.uses for rule in BASE.rules))

    assert set(DERIVED) <= used
    assert declared == set(PARAMETERS)


@pytest.mark.parametrize("case", CASES, ids=[case_id(case) for case in CASES])
def test_catalog_case(case):
    validation = validate({**CATALOG["defaults"], **case["input"]})
    assert validation.is_valid, validation.errors

    fired = {rule.id for rule in run(BASE, validation.values).fired}

    assert (case["rule"] in fired) is case["fires"]
