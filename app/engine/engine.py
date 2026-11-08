from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from app.engine.derived import COMPUTE
from app.engine.rules import AllOf, Comparison, Level, Node, Rule, RuleBase


class Facts(Mapping):
    def __init__(self, values: Mapping[str, object]):
        self._values = values
        self._derived: dict[str, object] = {}

    def __getitem__(self, key: str) -> object:
        if key in COMPUTE:
            if key not in self._derived:
                self._derived[key] = COMPUTE[key](self._values)
            return self._derived[key]
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._values
        yield from COMPUTE

    def __len__(self) -> int:
        return len(self._values) + len(COMPUTE)


def _compare(comparison: Comparison, facts: Mapping[str, object]) -> bool:
    actual = facts[comparison.field]
    expected = comparison.value
    if comparison.op == "=":
        return actual == expected
    if comparison.op == "≠":
        return actual != expected
    if comparison.op == "in":
        return actual in expected
    if actual is None:
        return False
    if comparison.op == "<":
        return actual < expected
    return actual >= expected


def evaluate(node: Node, facts: Mapping[str, object]) -> bool:
    if isinstance(node, Comparison):
        return _compare(node, facts)
    if isinstance(node, AllOf):
        return all(evaluate(child, facts) for child in node.conditions)
    return any(evaluate(child, facts) for child in node.conditions)


@dataclass(frozen=True)
class Result:
    fired: tuple[Rule, ...]
    derived: dict[str, object]

    def at_level(self, level: Level) -> tuple[Rule, ...]:
        return tuple(rule for rule in self.fired if rule.level is level)


def run(base: RuleBase, values: Mapping[str, object]) -> Result:
    facts = Facts(values)
    fired = tuple(rule for rule in base.rules if evaluate(rule.condition, facts))
    derived = {key: facts[key] for key in COMPUTE}
    return Result(fired, derived)
