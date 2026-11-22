from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import HTTPException

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
    SAVE_KINDS,
    Saved,
    consultation_count,
    entered_data,
    find_case,
    form_display,
    is_demo,
    label_error,
    local_time,
    normalize_label,
    review,
    save,
    summaries,
    timeline,
)
from app.scenarios import BY_SLUG, SCENARIOS, matching_scenario

bp = Blueprint("main", __name__)
bp.add_app_template_filter(local_time, "local_time")
bp.add_app_template_filter(consultation_count, "consultation_count")

ERROR_PAGES = {
    400: (
        "Nieprawidłowe zapytanie",
        "Serwer nie mógł odczytać wysłanych danych. Otwórz formularz i wyślij go jeszcze raz.",
    ),
    404: (
        "Nie znaleziono strony",
        "Pod tym adresem nie ma strony. Oznaczenie przypadku, numer konsultacji albo nazwa "
        "przykładu mogą być wpisane z błędem.",
    ),
    405: (
        "Niedozwolona metoda zapytania",
        "Ten adres przyjmuje tylko dane wysłane z formularza konsultacji. Otwórz formularz "
        "jeszcze raz.",
    ),
    500: (
        "Błąd serwera",
        "Wystąpił nieoczekiwany błąd i nie udało się przygotować strony. Spróbuj ponownie "
        "za chwilę.",
    ),
}
OTHER_ERROR = (
    "Nie udało się obsłużyć zapytania",
    "Serwer nie mógł obsłużyć tego zapytania. Wróć do strony głównej.",
)

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


def stored_form(case, consultation):
    form = form_display(consultation.parameters)
    if not is_demo(case.label):
        form[LABEL_FIELD] = case.label
    return form


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
        return render_form(stored_form(case, case.consultations[-1]))
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
    if label:
        saved = save(label, validation.values, result, base.version)
        return redirect(
            url_for(
                "main.saved_consultation", label=saved.label, number=saved.number, zapis=saved.kind
            ),
            303,
        )
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
        submitted=request.form,
        scenario=matching_scenario(data),
    )


@bp.post("/konsultacja/popraw")
def consultation_edit():
    return render_form(request.form)


@bp.get("/historia")
def history():
    cases = summaries(rule_base())
    return render_template(
        "history.html",
        demo_cases=sorted(
            (case for case in cases if is_demo(case.label)), key=lambda case: case.label
        ),
        cases=[case for case in cases if not is_demo(case.label)],
        rule_tips=all_rule_tips(),
    )


@bp.get("/historia/<label>")
def case_history(label):
    case = find_case(label)
    if case is None or not case.consultations:
        abort(404)
    return render_template(
        "case.html",
        case=case,
        entries=timeline(case, rule_base()),
        demo=is_demo(case.label),
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
    )


@bp.get("/historia/<label>/<int:number>")
def saved_consultation(label, number):
    case = find_case(label)
    if case is None or not 1 <= number <= len(case.consultations):
        abort(404)
    consultation = case.consultations[number - 1]
    base = rule_base()
    record = review(consultation, base)
    demo = is_demo(case.label)
    kind = request.args.get("zapis")
    saved = Saved.from_kind(case.label, number, kind) if kind in SAVE_KINDS and not demo else None
    form = stored_form(case, consultation)
    return render_template(
        "saved.html",
        case=case,
        number=number,
        consultation=consultation,
        record=record,
        entered=entered_data(record.values),
        result=record.result,
        explanations={
            rule.id: explain(base, rule, record.values, record.result.derived)
            for rule in record.result.fired
        },
        ptge_name=base.sources["ptge"].name,
        levels=LEVEL_TITLES,
        warnings=record.warnings,
        rule_tips=all_rule_tips(),
        rule_names=all_rule_names(),
        submitted=MultiDict(form),
        scenario=matching_scenario(form_display(consultation.parameters)),
        saved=saved,
        demo=demo,
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


@bp.app_errorhandler(HTTPException)
def error_page(error):
    title, message = ERROR_PAGES.get(error.code, OTHER_ERROR)
    page = render_template("error.html", code=error.code, title=title, message=message)
    return page, error.code, error.get_headers()
