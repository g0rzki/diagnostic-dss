from dataclasses import dataclass

from app.engine.parameters import PARAMETERS, Parameter

INTERVIEW_DEFAULTS = {
    "P2": "normalne",
    "P9": "nie wykonano",
    "P10": "nie",
    "P11": "nie",
    "P12": "nie omówiono",
    "P13": "nie wykonano",
    "P15": "nie badano",
    "P17": "nie",
}

HINTS = {
    "P1": "pełne lata, 18–120",
    "P2": "ograniczone oznacza także całkowitą eliminację glutenu przed diagnostyką",
    "P3": "w jednostkach laboratorium; wynik „< X” lub „> X” można wpisać ze znakiem",
    "P5": "w jednostkach laboratorium; wynik „< X” lub „> X” można wpisać ze znakiem",
    "P7": "wynik poniżej granicy oznaczalności wpisz jako 0",
    "P9": "dodatni, jeśli dodatni jest którykolwiek z wykonanych testów",
    "P11": "np. krwawienie z przewodu pokarmowego, dysfagia, objawy niedrożności",
    "P12": "ścieżka wchodzi w grę przy anty-TG2 IgA ≥ 10 × GGN; system wskaże, kiedy ją omówić",
    "P16": "tak, gdy schemat zakończono albo serologia w trakcie prowokacji jest dodatnia",
}


@dataclass(frozen=True)
class Section:
    title: str
    fields: tuple[Parameter, ...]


SECTIONS = tuple(
    Section(title, tuple(PARAMETERS[field] for field in fields))
    for title, fields in (
        ("Wywiad", ("P1", "P2", "P16", "P10", "P11", "P17")),
        ("Serologia", ("P3", "P4", "P5", "P6", "P7", "P8", "P9", "P12")),
        ("Histopatologia i HLA", ("P13", "P14", "P15")),
    )
)
