import re
from dataclasses import dataclass

from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS, Op, Parameter, ParamType
from app.engine.rules import Comparison, Level, Node, Rule, RuleBase

GROUPS = {
    "G1": (
        "serologia wstępna",
        "Punkt wejścia algorytmu: zlecenie badań pierwszego rzutu (anty-TG2 IgA z IgA "
        "całkowitym), wskazanie do badania u krewnych, ostrzeżenie o ograniczonym spożyciu "
        "glutenu, postępowanie przy niedoborze IgA przed testami IgG, interpretacja ujemnego "
        "wyniku przed biopsją.",
    ),
    "G2": (
        "ścieżka bez biopsji",
        "Anty-TG2 IgA ≥ 10 × GGN przed histologią: warunki wstępne ścieżki (wiek < 45 lat, "
        "brak objawów alarmowych, dieta z glutenem), wspólna decyzja z pacjentem, potwierdzenie "
        "w drugiej próbce i sytuacje, w których ścieżka nie ma zastosowania.",
    ),
    "G3": (
        "biopsja i histologia",
        "Wskazanie do biopsji i protokół pobrania wycinków, interpretacja stopnia Marsha "
        "w zestawieniu ze statusem serologii swoistej, ostrzeżenia o czynnikach, które mogą "
        "zaniżyć obraz histologiczny (ograniczony gluten, zbyt mała liczba wycinków).",
    ),
    "G4": (
        "sytuacje szczególne",
        "Niedobór IgA po wykonaniu testów IgG, pacjent na diecie ograniczonej (badanie HLA, "
        "potem prowokacja glutenem), stan po prowokacji, wykluczenie celiakii przez ujemny "
        "wynik HLA-DQ2/DQ8.",
    ),
}

LEVELS = {
    Level.RECOMMENDATION: "wskazuje kolejny krok diagnostyczny albo wniosek diagnostyczny",
    Level.WARNING: "sygnalizuje czynnik, który może zafałszować wynik",
    Level.INFORMATION: (
        "pokazuje niejednoznaczność lub rozbieżność źródeł albo opcję do rozważenia; "
        "decyzja należy do lekarza"
    ),
}

SOURCE_ROLES = {
    "esscd1": (
        "Źródło warunków reguł i ocen siły zaleceń (GRADE). Strony według paginacji czasopisma."
    ),
    "ptge": (
        "Zgodność z zaleceniami krajowymi, kierunek części reguł przy rozbieżności źródeł i polska "
        "terminologia. Strony według numeracji artykułu."
    ),
}

DEFINITIONS = {
    "D1": "dodatni, gdy P3 > P4; ujemny, gdy P3 ≤ P4; brak, gdy nie podano P3",
    "D1_2": "jak D1 dla drugiej próbki: P5 względem P6",
    "D2": "P3 ≥ 10 × P4",
    "D2_2": "P5 ≥ 10 × P6",
    "D3": (
        "całkowity, gdy P7 < 0,07 g/L; częściowy, gdy 0,07 g/L ≤ P7 < P8; norma, gdy P7 ≥ P8; "
        "brak, gdy nie podano P7"
    ),
    "D4": (
        "wysokie miano (D2), wiek < 45 lat, brak objawów alarmowych, spożycie glutenu "
        "normalne, histologia niewykonana, brak całkowitego niedoboru IgA i HLA nie ujemne"
    ),
    "D5": (
        "dodatnia, gdy anty-TG2 IgA jest dodatnie bez całkowitego niedoboru IgA albo testy IgG "
        "są dodatnie; ujemna, gdy anty-TG2 IgA jest ujemne przy IgA w normie, anty-TG2 IgA jest "
        "ujemne przy częściowym niedoborze IgA i ujemnych IgG albo przy całkowitym niedoborze IgA "
        "testy IgG są ujemne; nieustalona w pozostałych przypadkach"
    ),
    "D6": "P4 < P3 < 10 × P4 i brak całkowitego niedoboru IgA",
    "D7": "co najmniej 4 wycinki z części dalszej i co najmniej 1 z opuszki (P14)",
    "D8": "spożycie glutenu normalne (P2) albo prowokacja glutenem zakończona (P16 = tak)",
    "D9": (
        "ścieżka bez biopsji dostępna (D4), pacjent nie odmówił (P12 ≠ nie) i druga próbka "
        "nie jest ujemna (brak wyniku albo wynik dodatni)"
    ),
}


def rules_phrase(count: int) -> str:
    return "1 reguły" if count == 1 else f"{count} reguł"


@dataclass(frozen=True)
class ParameterEntry:
    param: Parameter
    values: str
    required: str
    rules: tuple[str, ...]

    @property
    def usage(self) -> str:
        return f"wykorzystywana w warunkach {rules_phrase(len(self.rules))}"


@dataclass(frozen=True)
class RuleEntry:
    rule: Rule
    source: str
    ptge: str


@dataclass(frozen=True)
class SourceEntry:
    name: str
    role: str
    citation: str
    doi: str


@dataclass(frozen=True)
class DerivedEntry:
    id: str
    label: str
    definition: str
    reads: tuple[str, ...]
    rules: tuple[str, ...]


def _number(value) -> str:
    return str(value).replace(".", ",")


def value_text(param: Parameter) -> str:
    if param.type is ParamType.ENUM:
        return " / ".join(param.values)
    if param.type is ParamType.BOOL:
        return "tak / nie"
    if param.type is ParamType.INT_PAIR:
        return f"dwie liczby całkowite ≥ {_number(param.min)} ({', '.join(param.parts)})"
    kind = "liczba całkowita" if param.type is ParamType.INT else "liczba"
    if param.min is not None and param.max is not None:
        text = f"{kind} {_number(param.min)}–{_number(param.max)}"
    elif param.min is not None:
        text = f"{kind} ≥ {_number(param.min)}"
    elif param.min_exclusive is not None:
        text = f"{kind} > {_number(param.min_exclusive)}"
    else:
        text = kind
    return f"{text} [{param.unit}]" if param.unit else text


def required_text(param: Parameter) -> str:
    condition = param.required_if
    if condition is None:
        return "tak" if param.required else "nie (brak wyniku jest dopuszczalny)"
    if condition.op is Op.GIVEN:
        return f"gdy podano {condition.param}"
    return f"gdy {condition.param} {condition.op.value} {condition.value}"


def _condition_fields(node: Node) -> set[str]:
    if isinstance(node, Comparison):
        return {node.field}
    return set().union(*(_condition_fields(child) for child in node.conditions))


def parameter_entries(base: RuleBase) -> list[ParameterEntry]:
    return [
        ParameterEntry(
            param,
            value_text(param),
            required_text(param),
            tuple(rule.id for rule in base.rules if param.id in rule.uses),
        )
        for param in PARAMETERS.values()
    ]


def _rules_reading(base: RuleBase, field: str) -> tuple[str, ...]:
    return tuple(rule.id for rule in base.rules if field in _condition_fields(rule.condition))


def derived_entries(base: RuleBase) -> list[DerivedEntry]:
    return [
        DerivedEntry(
            derived.id,
            derived.label,
            DEFINITIONS[derived.id],
            derived.reads,
            _rules_reading(base, derived.id),
        )
        for derived in DERIVED.values()
    ]


def _pages(pages) -> str:
    return ", ".join(str(page) for page in pages)


def source_pages(rule: Rule) -> tuple[str, ...]:
    pages = set(re.findall(r"s\. (\d+(?:–\d+)?)", rule.source.location)) or {str(rule.source.page)}
    return tuple(sorted(pages, key=lambda page: int(page.split("–")[0])))


def source_text(base: RuleBase, rule: Rule) -> str:
    return f"{base.sources[rule.source.ref].name}, s. {', '.join(source_pages(rule))}"


def ptge_text(rule: Rule) -> str:
    text = rule.ptge.status
    if rule.ptge.pages:
        text = f"{text}, s. {_pages(rule.ptge.pages)}"
    if rule.basis == "ptge":
        text = f"{text}; kierunek reguły według PTG-E"
    return text


def rules_by_group(base: RuleBase) -> list[tuple[str, str, str, list[RuleEntry]]]:
    return [
        (
            group,
            name,
            scope,
            [
                RuleEntry(rule, source_text(base, rule), ptge_text(rule))
                for rule in base.rules
                if rule.group == group
            ],
        )
        for group, (name, scope) in GROUPS.items()
    ]


def source_entries(base: RuleBase) -> list[SourceEntry]:
    entries = []
    for ref, reference in base.sources.items():
        citation, _, doi = reference.citation.partition(" doi:")
        entries.append(SourceEntry(reference.name, SOURCE_ROLES[ref], citation, doi.rstrip(".")))
    return entries


def parameter_tips(base: RuleBase) -> dict[str, str]:
    return {
        entry.param.id: (
            f"Dana wejściowa {entry.param.id}: {entry.param.label}. "
            f"Wartości: {entry.values}. Wymagana: {entry.required}. "
            f"{entry.usage[:1].upper()}{entry.usage[1:]}."
        )
        for entry in parameter_entries(base)
    }


def rule_tip(rule: Rule) -> str:
    name, _ = GROUPS[rule.group]
    return f"Reguła z grupy {rule.group} ({name}), poziom: {rule.level.value}."
