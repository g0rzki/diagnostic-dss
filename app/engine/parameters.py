from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ParamType(Enum):
    INT = "int"
    DECIMAL = "decimal"
    ENUM = "enum"
    BOOL = "bool"
    INT_PAIR = "int_pair"


class Op(Enum):
    GIVEN = "podano"
    EQ = "="
    NE = "≠"


@dataclass(frozen=True)
class Condition:
    param: str
    op: Op
    value: str | None = None


@dataclass(frozen=True)
class Parameter:
    id: str
    label: str
    type: ParamType
    required: bool = False
    required_if: Condition | None = None
    values: tuple[str, ...] = ()
    parts: tuple[str, ...] = ()
    min: Decimal | None = None
    max: Decimal | None = None
    min_exclusive: Decimal | None = None
    unit: str | None = None


_PARAMETERS = (
    Parameter(
        "P1", "wiek", ParamType.INT, required=True, min=Decimal(18), max=Decimal(120), unit="lata"
    ),
    Parameter(
        "P2",
        "spożycie glutenu w okresie badań",
        ParamType.ENUM,
        required=True,
        values=("normalne", "ograniczone"),
    ),
    Parameter("P3", "anty-TG2 IgA, wynik 1", ParamType.DECIMAL, min_exclusive=Decimal(0)),
    Parameter(
        "P4",
        "GGN laboratorium dla wyniku 1",
        ParamType.DECIMAL,
        required_if=Condition("P3", Op.GIVEN),
        min_exclusive=Decimal(0),
    ),
    Parameter(
        "P5", "anty-TG2 IgA, wynik 2 (druga próbka)", ParamType.DECIMAL, min_exclusive=Decimal(0)
    ),
    Parameter(
        "P6",
        "GGN laboratorium dla wyniku 2",
        ParamType.DECIMAL,
        required_if=Condition("P5", Op.GIVEN),
        min_exclusive=Decimal(0),
    ),
    Parameter("P7", "IgA całkowite", ParamType.DECIMAL, min=Decimal(0), unit="g/L"),
    Parameter(
        "P8",
        "dolna granica normy IgA całkowitego",
        ParamType.DECIMAL,
        required_if=Condition("P7", Op.GIVEN),
        min_exclusive=Decimal("0.07"),
        unit="g/L",
    ),
    Parameter(
        "P9",
        "testy IgG (anty-TG2 IgG / anty-DGP IgG)",
        ParamType.ENUM,
        required=True,
        values=("dodatni", "ujemny", "nie wykonano"),
    ),
    Parameter("P10", "objawy złego wchłaniania sugerujące celiakię", ParamType.BOOL, required=True),
    Parameter("P11", "objawy alarmowe", ParamType.BOOL, required=True),
    Parameter(
        "P12",
        "zgoda pacjenta na ścieżkę bez biopsji",
        ParamType.ENUM,
        required=True,
        values=("nie omówiono", "tak", "nie"),
    ),
    Parameter(
        "P13",
        "stopień Marsha",
        ParamType.ENUM,
        required=True,
        values=("nie wykonano", "0", "1", "2", "3"),
    ),
    Parameter(
        "P14",
        "liczba wycinków (część dalsza dwunastnicy, opuszka)",
        ParamType.INT_PAIR,
        required_if=Condition("P13", Op.NE, "nie wykonano"),
        parts=("dalsza", "opuszka"),
        min=Decimal(0),
    ),
    Parameter(
        "P15",
        "HLA-DQ2/DQ8",
        ParamType.ENUM,
        required=True,
        values=("dodatni", "ujemny", "nie badano"),
    ),
    Parameter(
        "P16",
        "prowokacja glutenem zakończona (wg zaleconego schematu)",
        ParamType.BOOL,
        required_if=Condition("P2", Op.EQ, "ograniczone"),
    ),
    Parameter("P17", "krewny 1. stopnia z celiakią", ParamType.BOOL, required=True),
)

PARAMETERS: dict[str, Parameter] = {p.id: p for p in _PARAMETERS}
