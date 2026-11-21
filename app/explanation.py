from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS
from app.engine.rules import Comparison, Grade, Node, Rule, RuleBase
from app.engine.validation import condition_met
from app.glossary import code_segments, ptge_text


@dataclass(frozen=True)
class Fact:
    id: str
    label: str
    value: object
    text: str


@dataclass(frozen=True)
class Explanation:
    condition_parts: tuple[tuple[str, bool], ...]
    facts: tuple[Fact, ...]
    inputs: tuple[Fact, ...]
    source: str
    evidence: str
    ptge: str


def _number(value: Decimal | int) -> str:
    return format(value, "f").replace(".", ",")


def _years(value: int) -> str:
    if value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14):
        return f"{value} lata"
    return f"{value} lat"


def not_applicable(field: str, values: Mapping[str, object]) -> bool:
    param = PARAMETERS.get(field)
    return (
        values[field] is None
        and param is not None
        and param.required_if is not None
        and not condition_met(param.required_if, values)
    )


def value_text(field: str, values: Mapping[str, object]) -> str:
    value = values[field]
    param = PARAMETERS.get(field)
    if value is None:
        return "nie dotyczy" if not_applicable(field, values) else "brak wyniku"
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, tuple):
        return f"część dalsza {value[0]}, opuszka {value[1]}"
    if isinstance(value, Decimal | int):
        if param and param.unit == "lata":
            return _years(value)
        text = _number(value)
        return f"{text} {param.unit}" if param and param.unit else text
    return str(value)


def condition_fields(node: Node) -> tuple[str, ...]:
    if isinstance(node, Comparison):
        return (node.field,)
    found = (field for child in node.conditions for field in condition_fields(child))
    return tuple(dict.fromkeys(found))


def _label(field: str) -> str:
    return PARAMETERS[field].label if field in PARAMETERS else DERIVED[field].label


def _fact(field: str, facts: Mapping[str, object]) -> Fact:
    return Fact(field, _label(field), facts[field], value_text(field, facts))


def grade_text(grade: Grade) -> str:
    parts = []
    if grade.certainty != "nie dotyczy":
        parts.append(f"pewność dowodów: {grade.certainty}")
    parts.append(f"siła zalecenia: {grade.strength}")
    if grade.agreement is not None:
        parts.append(f"zgoda {grade.agreement}%")
    return ", ".join(parts)


def evidence_text(rule: Rule) -> str:
    kind = rule.source.kind[:1].upper() + rule.source.kind[1:]
    if rule.source.grade is None:
        return f"{kind} (bez przypisanej oceny GRADE)"
    return f"{kind}; {grade_text(rule.source.grade)}"


def source_location(base: RuleBase, rule: Rule) -> str:
    text = f"{base.sources[rule.source.ref].name}: {rule.source.location}"
    return text if "s. " in rule.source.location else f"{text}, s. {rule.source.page}"


def explain(
    base: RuleBase, rule: Rule, values: Mapping[str, object], derived: Mapping[str, object]
) -> Explanation:
    facts = {**values, **derived}
    fields = condition_fields(rule.condition)
    inputs = tuple(
        _fact(field, facts)
        for field in rule.uses
        if field not in fields and not not_applicable(field, facts)
    )
    ptge = ptge_text(rule)
    if rule.ptge.grade:
        ptge = f"{ptge}; {grade_text(rule.ptge.grade)}"
    return Explanation(
        condition_parts=code_segments(rule.condition_text),
        facts=tuple(_fact(field, facts) for field in fields),
        inputs=inputs,
        source=source_location(base, rule),
        evidence=evidence_text(rule),
        ptge=ptge,
    )
