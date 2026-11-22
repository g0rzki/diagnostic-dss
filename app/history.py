import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from app.engine.engine import Result, run
from app.engine.parameters import PARAMETERS, ParamType
from app.engine.rules import Level, RuleBase
from app.engine.validation import Issue, validate
from app.explanation import value_text
from app.extensions import db
from app.models import LABEL_MAX_LENGTH, Case, Consultation

LABEL_FIELD = "oznaczenie"
LABEL = re.compile(rf"[^\W_][\w .-]{{0,{LABEL_MAX_LENGTH - 1}}}")
LABEL_ERROR = (
    f"oznaczenie przypadku: do {LABEL_MAX_LENGTH} znaków, dozwolone litery, cyfry, spacje"
    " oraz znaki „-”, „_” i „.”, na początku litera lub cyfra"
)
DEMO_PREFIXES = ("PRZYKŁAD", "PRZYKLAD")
RESERVED_ERROR = (
    "oznaczenie przypadku: oznaczenia zaczynające się od PRZYKŁAD są zarezerwowane dla przypadków"
    " pokazowych, wpisz własne oznaczenie"
)
LOCAL_TIME = ZoneInfo("Europe/Warsaw")
DECIMAL_FIELDS = {param.id for param in PARAMETERS.values() if param.type is ParamType.DECIMAL}


def normalize_label(raw: str | None) -> str:
    return " ".join((raw or "").split()).upper()


def is_demo(label: str) -> bool:
    return normalize_label(label).startswith(DEMO_PREFIXES)


def label_error(label: str) -> str | None:
    if not LABEL.fullmatch(label):
        return LABEL_ERROR
    return RESERVED_ERROR if is_demo(label) else None


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def form_values(values: Mapping[str, object]) -> dict[str, str]:
    form = {}
    for param in PARAMETERS.values():
        value = values[param.id]
        if param.type is ParamType.INT_PAIR:
            parts = value or (None,) * len(param.parts)
            for part, number in zip(param.parts, parts, strict=True):
                form[f"{param.id}_{part}"] = _text(number)
        else:
            form[param.id] = _text(value)
    return form


def parameter_values(stored: Mapping[str, str]) -> dict[str, object]:
    return validate(stored).values


def form_display(stored: Mapping[str, str]) -> dict[str, str]:
    """Zapisane dane do formularza: liczby dziesiętne z przecinkiem, tak jak wpisuje je lekarz."""
    return {
        name: value.replace(".", ",") if name in DECIMAL_FIELDS else value
        for name, value in stored.items()
    }


def local_time(moment: datetime) -> str:
    return moment.astimezone(LOCAL_TIME).strftime("%d.%m.%Y, %H:%M")


def consultation_count(number: int) -> str:
    if number == 1:
        return "1 konsultacja"
    if number % 10 in (2, 3, 4) and number % 100 not in (12, 13, 14):
        return f"{number} konsultacje"
    return f"{number} konsultacji"


def _recommendations(codes: list[str], base: RuleBase) -> tuple[str, ...]:
    levels = {rule.id: rule.level for rule in base.rules}
    return tuple(code for code in codes if levels.get(code) is Level.RECOMMENDATION)


def find_case(label: str) -> Case | None:
    return db.session.scalars(select(Case).where(Case.label == normalize_label(label))).first()


SAVE_KINDS = ("nowy", "kolejna", "bez-zmian")


@dataclass(frozen=True)
class Saved:
    label: str
    number: int
    created: bool
    new_case: bool

    @classmethod
    def from_kind(cls, label: str, number: int, kind: str) -> "Saved":
        return cls(label, number, created=kind != "bez-zmian", new_case=kind == "nowy")

    @property
    def kind(self) -> str:
        if self.new_case:
            return "nowy"
        return "kolejna" if self.created else "bez-zmian"

    @property
    def message(self) -> str:
        if self.new_case:
            return f"Utworzono przypadek {self.label} i zapisano pierwszą konsultację."
        if self.created:
            return f"Zapisano jako konsultację {self.number} przypadku {self.label}."
        return (
            f"Dane i wersja bazy reguł są takie same jak w ostatniej konsultacji przypadku"
            f" {self.label}, więc nowy wpis nie powstał."
        )


def save(label: str, values: Mapping[str, object], result: Result, version: str) -> Saved:
    statement = (
        insert(Case)
        .values(label=label)
        .on_conflict_do_nothing(index_elements=["label"])
        .returning(Case.id)
    )
    new_case = db.session.execute(statement).scalar() is not None
    case = db.session.scalars(select(Case).where(Case.label == label)).one()
    parameters = form_values(values)
    history = case.consultations
    if history and history[-1].parameters == parameters and history[-1].rules_version == version:
        return Saved(label, len(history), created=False, new_case=False)
    history.append(
        Consultation(
            parameters=parameters,
            derived=dict(result.derived),
            fired_rules=[rule.id for rule in result.fired],
            rules_version=version,
        )
    )
    db.session.commit()
    return Saved(label, len(history), created=True, new_case=new_case)


@dataclass(frozen=True)
class Change:
    field: str
    label: str
    before: str | None
    after: str


@dataclass(frozen=True)
class Entry:
    number: int
    consultation: Consultation
    changes: tuple[Change, ...]
    fired: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    recommendations: tuple[str, ...]
    previous_version: str | None


def _changes(
    before: Mapping[str, object] | None, after: Mapping[str, object]
) -> tuple[Change, ...]:
    changes = []
    for field, param in PARAMETERS.items():
        if before is None:
            if after[field] is not None:
                changes.append(Change(field, param.label, None, value_text(field, after)))
        elif before[field] != after[field]:
            changes.append(
                Change(field, param.label, value_text(field, before), value_text(field, after))
            )
    return tuple(changes)


def entered_data(values: Mapping[str, object]) -> tuple[Change, ...]:
    return _changes(None, values)


def timeline(case: Case, base: RuleBase) -> list[Entry]:
    entries = []
    previous = None
    previous_values = None
    for number, consultation in enumerate(case.consultations, start=1):
        values = parameter_values(consultation.parameters)
        fired = tuple(consultation.fired_rules)
        before = tuple(previous.fired_rules) if previous else ()
        version_changed = previous and previous.rules_version != consultation.rules_version
        entries.append(
            Entry(
                number=number,
                consultation=consultation,
                changes=_changes(previous_values, values),
                fired=fired,
                added=tuple(code for code in fired if previous and code not in before),
                removed=tuple(code for code in before if code not in fired),
                recommendations=_recommendations(consultation.fired_rules, base),
                previous_version=previous.rules_version if version_changed else None,
            )
        )
        previous, previous_values = consultation, values
    return entries


@dataclass(frozen=True)
class Review:
    values: dict[str, object]
    warnings: tuple[Issue, ...]
    result: Result
    missing: tuple[str, ...]
    current: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    stored_version: str
    current_version: str

    @property
    def same_version(self) -> bool:
        return self.stored_version == self.current_version

    @property
    def same_result(self) -> bool:
        return not self.added and not self.removed


def review(consultation: Consultation, base: RuleBase) -> Review:
    validation = validate(consultation.parameters)
    rules = {rule.id: rule for rule in base.rules}
    stored = tuple(consultation.fired_rules)
    current = tuple(rule.id for rule in run(base, validation.values).fired)
    return Review(
        values=validation.values,
        warnings=tuple(validation.warnings),
        result=Result(
            tuple(rules[code] for code in stored if code in rules), dict(consultation.derived)
        ),
        missing=tuple(code for code in stored if code not in rules),
        current=current,
        added=tuple(code for code in current if code not in stored),
        removed=tuple(code for code in stored if code not in current),
        stored_version=consultation.rules_version,
        current_version=base.version,
    )


@dataclass(frozen=True)
class Summary:
    label: str
    count: int
    last: datetime
    recommendations: tuple[str, ...]


def summaries(base: RuleBase) -> list[Summary]:
    found = []
    for case in db.session.scalars(select(Case).options(selectinload(Case.consultations))):
        if not case.consultations:
            continue
        last = case.consultations[-1]
        recommendations = _recommendations(last.fired_rules, base)
        found.append(Summary(case.label, len(case.consultations), last.created_at, recommendations))
    return sorted(found, key=lambda summary: summary.last, reverse=True)
