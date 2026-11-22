from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select, text

from app.engine.engine import run
from app.engine.rules import RuleBase
from app.engine.validation import validate
from app.extensions import MIGRATION_LOCK, db
from app.forms import INTERVIEW_DEFAULTS
from app.history import LOCAL_TIME, form_values
from app.models import Case, Consultation

SEROLOGY = {"P3": "150", "P4": "10", "P7": "1,5", "P8": "0,7"}
BIOPSY = {"P13": "3", "P14_dalsza": "4", "P14_opuszka": "1"}
LIMITED_GLUTEN = {"P2": "ograniczone", "P16": "nie"}


@dataclass(frozen=True)
class Stage:
    days_ago: int
    at: str
    data: Mapping[str, str]

    def moment(self, now: datetime) -> datetime:
        day = (now.astimezone(LOCAL_TIME) - timedelta(days=self.days_ago)).date()
        return datetime.combine(day, time.fromisoformat(self.at), LOCAL_TIME)


@dataclass(frozen=True)
class DemoCase:
    label: str
    stages: tuple[Stage, ...]


# Dane kolejnych wizyt: każdy etap dopisuje to, co pojawiło się od poprzedniej konsultacji
# (dni przed wstawieniem i godzina wizyty w czasie polskim). Wyniki reguł liczy silnik przy
# wstawianiu, więc przypadki zawsze odpowiadają bieżącej bazie.
DEMO_CASES = (
    DemoCase(
        "PRZYKŁAD-1",
        (
            Stage(84, "09:15", {"P1": "34"}),
            Stage(70, "10:40", SEROLOGY),
            Stage(63, "08:50", {"P12": "tak"}),
            Stage(49, "11:20", {"P5": "120", "P6": "10"}),
        ),
    ),
    DemoCase(
        "PRZYKŁAD-2",
        (
            Stage(77, "12:05", {"P1": "29", **SEROLOGY}),
            Stage(63, "09:30", {"P12": "tak"}),
            Stage(56, "13:45", {"P5": "8", "P6": "10"}),
            Stage(28, "10:10", BIOPSY),
        ),
    ),
    DemoCase(
        "PRZYKŁAD-3",
        (
            Stage(42, "08:20", {"P1": "41", "P10": "tak"}),
            Stage(35, "14:30", {"P3": "1", "P4": "10", "P7": "0,05", "P8": "0,7"}),
            Stage(14, "09:55", {"P9": "dodatni"}),
        ),
    ),
    DemoCase(
        "PRZYKŁAD-4",
        (
            Stage(147, "10:00", {"P1": "27", **LIMITED_GLUTEN, **SEROLOGY, "P3": "2"}),
            Stage(133, "11:35", {"P15": "dodatni"}),
            Stage(77, "12:50", {"P16": "tak", "P3": "60"}),
            Stage(56, "09:05", BIOPSY),
        ),
    ),
)


def demo_consultations(demo: DemoCase, base: RuleBase, now: datetime) -> list[Consultation]:
    data = dict(INTERVIEW_DEFAULTS)
    consultations = []
    for stage in demo.stages:
        data.update(stage.data)
        validation = validate(data)
        if validation.errors:
            raise ValueError(f"{demo.label}: niepoprawne dane etapu {stage.days_ago} dni temu")
        result = run(base, validation.values)
        consultations.append(
            Consultation(
                created_at=stage.moment(now),
                parameters=form_values(validation.values),
                derived=dict(result.derived),
                fired_rules=[rule.id for rule in result.fired],
                rules_version=base.version,
            )
        )
    return consultations


def insert_demo_cases(base: RuleBase) -> None:
    db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK})
    labels = [demo.label for demo in DEMO_CASES]
    existing = set(db.session.scalars(select(Case.label).where(Case.label.in_(labels))))
    now = datetime.now(UTC)
    for demo in DEMO_CASES:
        if demo.label not in existing:
            consultations = demo_consultations(demo, base, now)
            created = consultations[0].created_at
            db.session.add(Case(label=demo.label, created_at=created, consultations=consultations))
    db.session.commit()
