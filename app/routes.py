from flask import Blueprint, abort, current_app, render_template, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.engine.engine import run
from app.engine.parameters import PARAMETERS
from app.engine.rules import Level
from app.engine.validation import Issue, validate
from app.explanation import explain
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
from app.history import (
    LABEL_FIELD,
    consultation_count,
    find_case,
    form_display,
    label_error,
    local_time,
    normalize_label,
    save,
    summaries,
    timeline,
)
from app.scenarios import BY_SLUG, SCENARIOS, matching_scenario

bp = Blueprint("main", __name__)
bp.add_app_template_filter(local_time, "local_time")
bp.add_app_template_filter(consultation_count, "consultation_count")

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


def split_form(form):
    data = {name: value for name, value in form.items() if name != LABEL_FIELD}
    return form.get(LABEL_FIELD, ""), data


@bp.get("/")
def index():
    return render_template("index.html")


def render_form(values, errors=(), status=200):
    _, data = split_form(values)
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
        other_errors=[
            issue.message
            for issue in errors
            if issue.field not in PARAMETERS and issue.field != LABEL_FIELD
        ],
        scenarios=SCENARIOS,
        scenario=matching_scenario(data),
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
    )
    return page, status


@bp.get("/konsultacja")
def consultation_form():
    case_label = request.args.get("przypadek")
    if case_label is not None:
        case = find_case(case_label)
        if case is None or not case.consultations:
            abort(404)
        last = form_display(case.consultations[-1].parameters)
        return render_form({**last, LABEL_FIELD: case.label})
    slug = request.args.get("przyklad")
    if slug is None:
        return render_form(INTERVIEW_DEFAULTS)
    if slug not in BY_SLUG:
        abort(404)
    return render_form(BY_SLUG[slug].values)


@bp.post("/konsultacja")
def consultation_result():
    raw_label, data = split_form(request.form)
    label = normalize_label(raw_label)
    validation = validate(data)
    errors = list(validation.errors)
    if label and (problem := label_error(label)):
        errors.append(Issue(LABEL_FIELD, problem))
    if errors:
        return render_form(request.form, errors, 422)
    base = rule_base()
    result = run(base, validation.values)
    saved = save(label, validation.values, result, base.version) if label else None
    submitted = request.form.copy()
    if LABEL_FIELD in submitted:
        submitted[LABEL_FIELD] = label
    return render_template(
        "result.html",
        result=result,
        explanations={
            rule.id: explain(base, rule, validation.values, result.derived) for rule in result.fired
        },
        ptge_name=base.sources["ptge"].name,
        levels=LEVEL_TITLES,
        warnings=validation.warnings,
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
        submitted=submitted,
        scenario=matching_scenario(data),
        saved=saved,
    )


@bp.post("/konsultacja/popraw")
def consultation_edit():
    return render_form(request.form)


@bp.get("/historia")
def history():
    return render_template("history.html", cases=summaries(rule_base()), rule_tips=all_rule_tips())


@bp.get("/historia/<label>")
def case_history(label):
    case = find_case(label)
    if case is None or not case.consultations:
        abort(404)
    return render_template(
        "case.html",
        case=case,
        entries=timeline(case, rule_base()),
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
    )


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
