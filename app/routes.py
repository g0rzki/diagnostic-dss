from flask import Blueprint, abort, current_app, render_template, request
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
from app.scenarios import BY_SLUG, SCENARIOS, matching_scenario

bp = Blueprint("main", __name__)

LEVEL_TITLES = (
    (Level.RECOMMENDATION, "Rekomendacje", LEVELS[Level.RECOMMENDATION]),
    (Level.WARNING, "Ostrzeżenia", LEVELS[Level.WARNING]),
    (Level.INFORMATION, "Informacje", LEVELS[Level.INFORMATION]),
)


def rule_base():
    return current_app.extensions["rule_base"]


def all_rule_tips():
    return {rule.id: rule_tip(rule) for rule in rule_base().rules}


def all_rule_names():
    return {rule.id: rule.name[:1].upper() + rule.name[1:] for rule in rule_base().rules}


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
        scenarios=SCENARIOS,
        scenario=matching_scenario(values),
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
    )
    return page, status


@bp.get("/konsultacja")
def consultation_form():
    slug = request.args.get("przyklad")
    if slug is None:
        return render_form(INTERVIEW_DEFAULTS)
    if slug not in BY_SLUG:
        abort(404)
    return render_form(BY_SLUG[slug].values)


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
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
        submitted=request.form,
        scenario=matching_scenario(request.form),
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
        ptge_name=base.sources["ptge"].name,
    )


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "error", "database": "unavailable"}, 503
    return {"status": "ok", "database": "ok"}
