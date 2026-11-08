from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path

import yaml

from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS, ParamType


class Level(Enum):
    RECOMMENDATION = "rekomendacja"
    WARNING = "ostrzeżenie"
    INFORMATION = "informacja"


OPERATORS = ("=", "≠", "in", "<", "≥")
ORDER_OPERATORS = ("<", "≥")
SOURCE_KINDS = ("zalecenie", "uzasadnienie", "tabela")
PTGE_STATUSES = ("zgodność", "różnica", "brak odniesienia")
CERTAINTIES = ("wysoka", "umiarkowana", "niska", "nie dotyczy")
STRENGTHS = ("silne", "warunkowe", "dobra praktyka (UGPS)", "opinia ekspercka")
REQUIRED_KEYS = {
    "id",
    "name",
    "group",
    "level",
    "uses",
    "condition_text",
    "condition",
    "conclusion",
    "source",
    "ptge",
}
OPTIONAL_KEYS = {"basis"}
SOURCE_KEYS = {"ref", "location", "page", "kind", "grade"}
PTGE_KEYS = {"status", "pages", "grade"}


@dataclass(frozen=True)
class Comparison:
    field: str
    op: str
    value: object


@dataclass(frozen=True)
class AllOf:
    conditions: tuple["Node", ...]


@dataclass(frozen=True)
class AnyOf:
    conditions: tuple["Node", ...]


Node = Comparison | AllOf | AnyOf


@dataclass(frozen=True)
class Grade:
    certainty: str
    strength: str
    agreement: int | None


@dataclass(frozen=True)
class Source:
    ref: str
    location: str
    page: int
    kind: str
    grade: Grade | None


@dataclass(frozen=True)
class Ptge:
    status: str
    pages: tuple[int, ...]
    grade: Grade | None


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    group: str
    level: Level
    basis: str | None
    uses: tuple[str, ...]
    condition_text: str
    condition: Node
    conclusion: str
    source: Source
    ptge: Ptge


@dataclass(frozen=True)
class Reference:
    name: str
    citation: str


@dataclass(frozen=True)
class RuleBase:
    sources: dict[str, Reference]
    rules: tuple[Rule, ...]


class RuleFileError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("błędy w plikach reguł:\n" + "\n".join(problems))
        self.problems = problems


class InvalidRule(ValueError):
    pass


def _field_type(field: str) -> tuple[ParamType, tuple[str, ...]]:
    if field in PARAMETERS:
        return PARAMETERS[field].type, PARAMETERS[field].values
    if field in DERIVED:
        return DERIVED[field].type, DERIVED[field].values
    raise InvalidRule(f"nieznane pole {field!r}")


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_keys(raw: Mapping, allowed: set[str], where: str) -> None:
    if unknown := set(raw) - allowed:
        raise InvalidRule(f"{where}: nieznane pola {sorted(unknown)}")


def _parse_value(field: str, value: object) -> object:
    field_type, allowed = _field_type(field)
    if value is None:
        if field in DERIVED:
            raise InvalidRule(f"{field}: wartość pochodna jest zawsze ustalona, null niedozwolone")
        return None
    if field_type is ParamType.ENUM:
        if value not in allowed:
            raise InvalidRule(f"{field}: wartość {value!r} spoza listy {list(allowed)}")
        return value
    if field_type is ParamType.BOOL:
        if not isinstance(value, bool):
            raise InvalidRule(f"{field}: wymagane true / false, jest {value!r}")
        return value
    if field_type in (ParamType.INT, ParamType.DECIMAL):
        if not _is_number(value):
            raise InvalidRule(f"{field}: wymagana liczba, jest {value!r}")
        return Decimal(str(value))
    raise InvalidRule(f"{field}: pole tego typu można porównać tylko z null")


def _parse_comparison(raw: list) -> Comparison:
    if len(raw) != 3:
        raise InvalidRule(f"porównanie musi mieć postać [pole, operator, wartość], jest {raw!r}")
    field, op, value = raw
    if not isinstance(field, str):
        raise InvalidRule(f"nazwa pola musi być napisem, jest {field!r}")
    if op not in OPERATORS:
        raise InvalidRule(f"{field}: nieznany operator {op!r}, dozwolone {list(OPERATORS)}")
    if op in ORDER_OPERATORS:
        field_type, _ = _field_type(field)
        if field_type not in (ParamType.INT, ParamType.DECIMAL):
            raise InvalidRule(f"{field}: operator {op!r} tylko dla pól liczbowych")
        if value is None:
            raise InvalidRule(f"{field}: operator {op!r} wymaga liczby")
    if op == "in":
        if not isinstance(value, list) or not value:
            raise InvalidRule(f"{field}: operator 'in' wymaga niepustej listy")
        return Comparison(field, op, tuple(_parse_value(field, item) for item in value))
    return Comparison(field, op, _parse_value(field, value))


def _parse_node(raw: object) -> Node:
    if isinstance(raw, list):
        return _parse_comparison(raw)
    if isinstance(raw, Mapping) and len(raw) == 1:
        ((key, items),) = raw.items()
        if key in ("all", "any"):
            if not isinstance(items, list) or not items:
                raise InvalidRule(f"'{key}' wymaga niepustej listy warunków")
            nodes = tuple(_parse_node(item) for item in items)
            return AllOf(nodes) if key == "all" else AnyOf(nodes)
    raise InvalidRule(f"nieprawidłowy warunek {raw!r}, oczekiwano porównania, 'all' albo 'any'")


def _fields(node: Node) -> set[str]:
    if isinstance(node, Comparison):
        return {node.field}
    return set().union(*(_fields(child) for child in node.conditions))


def _check_uses(uses: tuple[str, ...], condition: Node) -> None:
    fields = _fields(condition)
    direct = {field for field in fields if field in PARAMETERS}
    derived = [DERIVED[field] for field in fields if field in DERIVED]
    reachable = direct.union(*(d.reads for d in derived))
    declared = set(uses)
    if missing := direct - declared:
        raise InvalidRule(f"uses: brak parametrów czytanych wprost przez warunek {sorted(missing)}")
    if extra := declared - reachable:
        raise InvalidRule(f"uses: parametry, których warunek nie czyta {sorted(extra)}")
    for d in derived:
        if not declared & set(d.reads):
            raise InvalidRule(
                f"uses: żaden parametr wartości {d.id} {list(d.reads)} nie jest w uses"
            )


def _parse_uses(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise InvalidRule("uses: wymagana niepusta lista parametrów")
    if unknown := [item for item in raw if item not in PARAMETERS]:
        raise InvalidRule(f"uses: nieznane parametry {unknown}")
    if len(set(raw)) != len(raw):
        raise InvalidRule("uses: powtórzone parametry")
    return tuple(raw)


def _choice(raw: Mapping, key: str, allowed: tuple[str, ...], where: str) -> str:
    value = raw.get(key)
    if value not in allowed:
        raise InvalidRule(f"{where}.{key}: wartość {value!r} spoza listy {list(allowed)}")
    return value


def _parse_grade(raw: object, where: str) -> Grade | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or set(raw) - {"certainty", "strength", "agreement"}:
        raise InvalidRule(f"{where}.grade: dozwolone pola certainty, strength, agreement")
    agreement = raw.get("agreement")
    if agreement is not None and not (_is_int(agreement) and 0 <= agreement <= 100):
        raise InvalidRule(f"{where}.grade.agreement: wymagana liczba całkowita 0–100")
    return Grade(
        _choice(raw, "certainty", CERTAINTIES, f"{where}.grade"),
        _choice(raw, "strength", STRENGTHS, f"{where}.grade"),
        agreement,
    )


def _parse_source(raw: object, sources: Mapping[str, Reference]) -> Source:
    if not isinstance(raw, Mapping):
        raise InvalidRule("source: wymagany słownik")
    _check_keys(raw, SOURCE_KEYS, "source")
    if raw.get("ref") not in sources:
        raise InvalidRule(f"source.ref: nieznane źródło {raw.get('ref')!r}")
    if not isinstance(raw.get("location"), str) or not raw["location"]:
        raise InvalidRule("source.location: wymagany opis miejsca w wytycznych")
    if not _is_int(raw.get("page")):
        raise InvalidRule("source.page: wymagany numer strony")
    return Source(
        raw["ref"],
        raw["location"],
        raw["page"],
        _choice(raw, "kind", SOURCE_KINDS, "source"),
        _parse_grade(raw.get("grade"), "source"),
    )


def _parse_ptge(raw: object) -> Ptge:
    if not isinstance(raw, Mapping):
        raise InvalidRule("ptge: wymagany słownik")
    _check_keys(raw, PTGE_KEYS, "ptge")
    status = _choice(raw, "status", PTGE_STATUSES, "ptge")
    pages = raw.get("pages", [])
    if not isinstance(pages, list) or not all(_is_int(page) for page in pages):
        raise InvalidRule("ptge.pages: wymagana lista numerów stron")
    if (status == "brak odniesienia") != (not pages):
        raise InvalidRule("ptge.pages: strony podaje się wtedy i tylko wtedy, gdy PTG-E się odnosi")
    return Ptge(status, tuple(pages), _parse_grade(raw.get("grade"), "ptge"))


def _text(raw: Mapping, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRule(f"{key}: wymagany niepusty tekst")
    return value


def _parse_rule(raw: object, group: str, sources: Mapping[str, Reference]) -> Rule:
    if not isinstance(raw, Mapping):
        raise InvalidRule("reguła musi być słownikiem")
    if missing := REQUIRED_KEYS - set(raw):
        raise InvalidRule(f"brak pól {sorted(missing)}")
    if unknown := set(raw) - REQUIRED_KEYS - OPTIONAL_KEYS:
        raise InvalidRule(f"nieznane pola {sorted(unknown)}")
    if raw["group"] != group:
        raise InvalidRule(f"group: {raw['group']!r} niezgodne z plikiem ({group})")
    if not isinstance(raw["id"], str) or not raw["id"].startswith(f"{group}-"):
        raise InvalidRule(f"id: musi zaczynać się od {group}-")
    levels = tuple(level.value for level in Level)
    if raw["level"] not in levels:
        raise InvalidRule(f"level: wartość {raw['level']!r} spoza listy {list(levels)}")
    if raw.get("basis") not in (None, "ptge"):
        raise InvalidRule("basis: dozwolona tylko wartość ptge")
    uses = _parse_uses(raw["uses"])
    condition = _parse_node(raw["condition"])
    _check_uses(uses, condition)
    return Rule(
        id=raw["id"],
        name=_text(raw, "name"),
        group=group,
        level=Level(raw["level"]),
        basis=raw.get("basis"),
        uses=uses,
        condition_text=_text(raw, "condition_text"),
        condition=condition,
        conclusion=_text(raw, "conclusion"),
        source=_parse_source(raw["source"], sources),
        ptge=_parse_ptge(raw["ptge"]),
    )


def _read_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _load_sources(path: Path) -> dict[str, Reference]:
    raw = _read_yaml(path)
    if not isinstance(raw, Mapping) or not raw:
        raise InvalidRule("wymagany słownik źródeł")
    sources = {}
    for ref, entry in raw.items():
        if not isinstance(entry, Mapping) or set(entry) != {"name", "citation"}:
            raise InvalidRule(f"{ref}: wymagane pola name i citation")
        if not all(isinstance(entry[key], str) and entry[key].strip() for key in entry):
            raise InvalidRule(f"{ref}: name i citation muszą być niepustym tekstem")
        sources[ref] = Reference(entry["name"], entry["citation"])
    return sources


def load_rules(directory: Path) -> RuleBase:
    problems: list[str] = []
    try:
        sources = _load_sources(directory / "sources.yaml")
    except (OSError, yaml.YAMLError, InvalidRule) as error:
        raise RuleFileError([f"sources.yaml: {error}"]) from None

    rules: list[Rule] = []
    seen: set[str] = set()
    files = sorted(directory.glob("g*.yaml"))
    if not files:
        problems.append(f"{directory}: brak plików reguł g*.yaml")
    for path in files:
        group = path.stem.upper()
        try:
            raw = _read_yaml(path)
        except yaml.YAMLError as error:
            problems.append(f"{path.name}: błąd składni YAML: {error}")
            continue
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"rules"}
            or not isinstance(raw["rules"], list)
        ):
            problems.append(f"{path.name}: plik musi zawierać wyłącznie listę 'rules'")
            continue
        for index, entry in enumerate(raw["rules"], start=1):
            rule_id = entry.get("id") if isinstance(entry, Mapping) else None
            label = rule_id if isinstance(rule_id, str) else f"#{index}"
            if isinstance(rule_id, str):
                if rule_id in seen:
                    problems.append(f"{path.name}: {label}: powtórzone id")
                    continue
                seen.add(rule_id)
            try:
                rules.append(_parse_rule(entry, group, sources))
            except InvalidRule as error:
                problems.append(f"{path.name}: {label}: {error}")

    if problems:
        raise RuleFileError(problems)
    return RuleBase(sources, tuple(rules))
