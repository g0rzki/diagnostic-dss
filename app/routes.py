from flask import Blueprint, current_app, render_template, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.engine.engine import run
from app.engine.parameters import PARAMETERS
from app.engine.rules import Level
from app.engine.validation import validate
from app.extensions import db
from app.forms import HINTS, INTERVIEW_DEFAULTS, SECTIONS
from app.glossary import (
    LEVELS,
    derived_entries,
    parameter_entries,
    parameter_tips,
    rule_tip,
    rules_by_group,
    source_entries,
)

bp = Blueprint("main", __name__)

LEVEL_TITLES = (
    (Level.RECOMMENDATION, "Rekomendacje", LEVELS[Level.RECOMMENDATION]),
    (Level.WARNING, "Ostrzeżenia", LEVELS[Level.WARNING]),
    (Level.INFORMATION, "Informacje", LEVELS[Level.INFORMATION]),
)


def rule_base():
    return current_app.extensions["rule_base"]


@bp.get("/")
def index():
    return render_template("index.html")


def render_form(values, errors=(), status=200):
    errors_by_field = {}
    for issue in errors:
        errors_by_field.setdefault(issue.field, []).append(issue.message)
    page = render_template(
        "consultation.html",
        sections=SECTIONS,
        hints=HINTS,
        tips=parameter_tips(rule_base()),
        values=values,
        errors=errors_by_field,
        other_errors=[issue.message for issue in errors if issue.field not in PARAMETERS],
    )
    return page, status


@bp.get("/konsultacja")
def consultation_form():
    return render_form(INTERVIEW_DEFAULTS)


@bp.post("/konsultacja")
def consultation_result():
    validation = validate(request.form)
    if not validation.is_valid:
        return render_form(request.form, validation.errors, 422)
    result = run(rule_base(), validation.values)
    return render_template(
        "result.html",
        result=result,
        levels=LEVEL_TITLES,
        warnings=validation.warnings,
        rule_tips={rule.id: rule_tip(rule) for rule in result.fired},
        submitted=request.form,
    )


@bp.post("/konsultacja/popraw")
def consultation_edit():
    return render_form(request.form)


@bp.get("/slownik")
def glossary():
    base = rule_base()
    return render_template(
        "glossary.html",
        levels=[(level.value.capitalize(), text) for level, text in LEVELS.items()],
        parameters=parameter_entries(base),
        derived=derived_entries(base),
        groups=rules_by_group(base),
        sources=source_entries(base),
    )


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "error", "database": "unavailable"}, 503
    return {"status": "ok", "database": "ok"}
