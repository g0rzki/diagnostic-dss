from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.engine.parameters import ParamType
from app.engine.validation import TOTAL_IGA_DEFICIENCY


@dataclass(frozen=True)
class Derived:
    id: str
    label: str
    type: ParamType
    reads: tuple[str, ...]
    values: tuple[str, ...] = ()


ANTIBODY_RESULT = ("brak", "ujemny", "dodatni")

_DERIVED = (
    Derived("D1", "anty-TG2 IgA, wynik 1", ParamType.ENUM, ("P3", "P4"), ANTIBODY_RESULT),
    Derived("D1_2", "anty-TG2 IgA, wynik 2", ParamType.ENUM, ("P5", "P6"), ANTIBODY_RESULT),
    Derived("D2", "wysokie miano anty-TG2 IgA", ParamType.BOOL, ("P3", "P4")),
    Derived("D2_2", "wysokie miano anty-TG2 IgA w drugiej próbce", ParamType.BOOL, ("P5", "P6")),
    Derived(
        "D3",
        "IgA całkowite – niedobór całkowity / częściowy / norma",
        ParamType.ENUM,
        ("P7", "P8"),
        ("brak", "całkowity", "częściowy", "norma"),
    ),
    Derived(
        "D4",
        "ścieżka bez biopsji dostępna",
        ParamType.BOOL,
        ("P1", "P2", "P3", "P4", "P7", "P11", "P13", "P15"),
    ),
    Derived(
        "D5",
        "status serologii swoistej dla celiakii",
        ParamType.ENUM,
        ("P3", "P4", "P7", "P8", "P9"),
        ("dodatnia", "ujemna", "nieustalona"),
    ),
    Derived("D6", "niskie miano anty-TG2 IgA", ParamType.BOOL, ("P3", "P4", "P7")),
    Derived("D7", "wystarczająca liczba wycinków", ParamType.BOOL, ("P14",)),
    Derived("D8", "spożycie glutenu wystarczające do oceny", ParamType.BOOL, ("P2", "P16")),
    Derived(
        "D9",
        "ścieżka bez biopsji w toku",
        ParamType.BOOL,
        ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P11", "P12", "P13", "P15"),
    ),
)

DERIVED: dict[str, Derived] = {d.id: d for d in _DERIVED}


def _antibody_result(values: Mapping[str, object], result: str, limit: str) -> str:
    if values[result] is None:
        return "brak"
    return "dodatni" if values[result] > values[limit] else "ujemny"


def _high_titre(values: Mapping[str, object], result: str, limit: str) -> bool:
    return values[result] is not None and values[result] >= 10 * values[limit]


def _total_iga_deficiency(values: Mapping[str, object]) -> bool:
    return values["P7"] is not None and values["P7"] < TOTAL_IGA_DEFICIENCY


def d1(values: Mapping[str, object]) -> str:
    return _antibody_result(values, "P3", "P4")


def d1_2(values: Mapping[str, object]) -> str:
    return _antibody_result(values, "P5", "P6")


def d2(values: Mapping[str, object]) -> bool:
    return _high_titre(values, "P3", "P4")


def d2_2(values: Mapping[str, object]) -> bool:
    return _high_titre(values, "P5", "P6")


def d3(values: Mapping[str, object]) -> str:
    if values["P7"] is None:
        return "brak"
    if _total_iga_deficiency(values):
        return "całkowity"
    return "częściowy" if values["P7"] < values["P8"] else "norma"


def d4(values: Mapping[str, object]) -> bool:
    return (
        d2(values)
        and values["P1"] < 45
        and values["P11"] is False
        and values["P2"] == "normalne"
        and values["P13"] == "nie wykonano"
        and not _total_iga_deficiency(values)
        and values["P15"] != "ujemny"
    )


def d5(values: Mapping[str, object]) -> str:
    tg2 = d1(values)
    if (tg2 == "dodatni" and not _total_iga_deficiency(values)) or values["P9"] == "dodatni":
        return "dodatnia"
    iga = d3(values)
    if (
        (tg2 == "ujemny" and iga == "norma")
        or (tg2 == "ujemny" and iga == "częściowy" and values["P9"] == "ujemny")
        or (iga == "całkowity" and values["P9"] == "ujemny")
    ):
        return "ujemna"
    return "nieustalona"


def d6(values: Mapping[str, object]) -> bool:
    return d1(values) == "dodatni" and not d2(values) and not _total_iga_deficiency(values)


def d7(values: Mapping[str, object]) -> bool:
    return values["P14"] is not None and values["P14"][0] >= 4 and values["P14"][1] >= 1


def d8(values: Mapping[str, object]) -> bool:
    return values["P2"] == "normalne" or values["P16"] is True


def d9(values: Mapping[str, object]) -> bool:
    return d4(values) and values["P12"] != "nie" and d1_2(values) != "ujemny"


COMPUTE: dict[str, Callable[[Mapping[str, object]], object]] = {
    "D1": d1,
    "D1_2": d1_2,
    "D2": d2,
    "D2_2": d2_2,
    "D3": d3,
    "D4": d4,
    "D5": d5,
    "D6": d6,
    "D7": d7,
    "D8": d8,
    "D9": d9,
}
