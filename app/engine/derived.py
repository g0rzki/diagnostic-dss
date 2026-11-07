from dataclasses import dataclass

from app.engine.parameters import ParamType


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
