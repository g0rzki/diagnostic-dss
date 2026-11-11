from collections.abc import Mapping
from dataclasses import dataclass

from app.forms import INTERVIEW_DEFAULTS


@dataclass(frozen=True)
class Variant:
    change: str
    values: dict[str, str]
    expected: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    slug: str
    title: str
    summary: str
    data: dict[str, str]
    path: tuple[str, ...]
    expected: tuple[str, ...]
    variants: tuple[Variant, ...]

    @property
    def values(self) -> dict[str, str]:
        return {**INTERVIEW_DEFAULTS, **self.data}


SCENARIOS = (
    Scenario(
        slug="bez-biopsji",
        title="Rozpoznanie bez biopsji",
        summary="Wysokie miano anty-TG2 IgA, zgoda pacjenta i dodatnia druga próbka.",
        data={
            "P1": "30",
            "P3": "150",
            "P4": "10",
            "P5": "120",
            "P6": "10",
            "P7": "1,5",
            "P8": "0,7",
            "P12": "tak",
        },
        path=(
            "Anty-TG2 IgA 150 przy GGN 10 to 15 × GGN, czyli wysokie miano (D2).",
            "Wiek poniżej 45 lat, brak objawów alarmowych, dieta z glutenem, IgA całkowite "
            "w normie i HLA nie ujemne: ścieżka bez biopsji jest dostępna (D4).",
            "Pacjent wyraził zgodę (P12), a druga próbka 120 przy GGN 10 jest dodatnia (D1_2).",
            "Ścieżka jest w toku (D9), więc protokół biopsji (G3-03) się nie pojawia.",
        ),
        expected=("G2-03",),
        variants=(
            Variant("wynik 2 (P5) zmień na 8", {"P5": "8"}, ("G2-05", "G3-03")),
            Variant("wiek (P1) zmień na 45", {"P1": "45"}, ("G2-07", "G3-03")),
        ),
    ),
    Scenario(
        slug="biopsja-marsh-2",
        title="Biopsja przy niskim mianie",
        summary="Niskie miano anty-TG2 IgA i Marsh 2: wytyczne ESsCD i PTG-E się różnią.",
        data={
            "P1": "50",
            "P3": "25",
            "P4": "10",
            "P7": "1,5",
            "P8": "0,7",
            "P13": "2",
            "P14_dalsza": "4",
            "P14_opuszka": "1",
        },
        path=(
            "Anty-TG2 IgA 25 przy GGN 10 to 2,5 × GGN: wynik dodatni, ale niskie miano (D6).",
            "Przed histologią system wskazałby biopsję (G3-01) i protokół pobrania wycinków "
            "(G3-03).",
            "Pobrano 4 wycinki z części dalszej i 1 z opuszki, czyli wystarczająco (D7).",
            "Marsh 2 przy niskim mianie: zalecenie ESsCD uznaje rozpoznanie za potwierdzone, "
            "a PTG-E opisuje szarą strefę. Kierunek reguły pochodzi z PTG-E, stanowisko ESsCD "
            "jest podane we wniosku.",
        ),
        expected=("G3-07",),
        variants=(
            Variant("stopień Marsha (P13) zmień na 3", {"P13": "3"}, ("G3-05",)),
            Variant("stopień Marsha (P13) zmień na 0", {"P13": "0"}, ("G3-08",)),
        ),
    ),
    Scenario(
        slug="niedobor-iga",
        title="Całkowity niedobór IgA",
        summary="IgA całkowite poniżej 0,07 g/L, ujemne testy IgG i objawy złego wchłaniania.",
        data={
            "P1": "30",
            "P3": "1",
            "P4": "10",
            "P7": "0,05",
            "P8": "0,7",
            "P9": "ujemny",
            "P10": "tak",
        },
        path=(
            "IgA całkowite 0,05 g/L to całkowity niedobór IgA (D3), więc ujemny wynik "
            "anty-TG2 IgA jest niewiarygodny.",
            "Testy IgG są ujemne, więc serologia swoista jest ujemna (D5), ale przy niedoborze IgA "
            "nie wyklucza celiakii.",
            "Objawy złego wchłaniania (P10): ESsCD zaleca biopsję mimo ujemnych testów IgG "
            "(G4-02).",
            "Informacja G4-03 mówi, że celiakii nie potwierdzono, i kiedy rozważyć badanie HLA.",
        ),
        expected=("G4-02", "G4-03"),
        variants=(
            Variant(
                "testy IgG (P9) zmień na dodatni",
                {"P9": "dodatni"},
                ("G3-03", "G4-01"),
            ),
        ),
    ),
    Scenario(
        slug="dieta-bezglutenowa",
        title="Pacjent na diecie bezglutenowej",
        summary="Ograniczony gluten, ujemna serologia i dodatnie HLA-DQ2/DQ8.",
        data={
            "P1": "30",
            "P2": "ograniczone",
            "P16": "nie",
            "P3": "2",
            "P4": "10",
            "P7": "1,5",
            "P8": "0,7",
            "P15": "dodatni",
        },
        path=(
            "Spożycie glutenu jest ograniczone, a prowokacji nie zakończono, więc gluten "
            "jest niewystarczający do oceny (D8).",
            "Ujemny wynik anty-TG2 IgA może być przez to fałszywie ujemny (ostrzeżenie G1-02).",
            "HLA-DQ2/DQ8 jest dodatnie, więc celiakii nie da się wykluczyć genetycznie: system "
            "wskazuje prowokację glutenem z dawkami według PTG-E i minimum ESsCD (G4-06).",
        ),
        expected=("G4-06", "G1-02"),
        variants=(Variant("HLA (P15) zmień na ujemny", {"P15": "ujemny"}, ("G4-05",)),),
    ),
)

BY_SLUG = {scenario.slug: scenario for scenario in SCENARIOS}


def matching_scenario(form: Mapping[str, str]) -> Scenario | None:
    filled = {name: value for name, value in form.items() if str(value).strip()}
    for scenario in SCENARIOS:
        if filled == scenario.values:
            return scenario
    return None
