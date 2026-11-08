from app.engine.parameters import PARAMETERS
from app.engine.validation import validate
from app.forms import HINTS, INTERVIEW_DEFAULTS, SECTIONS


def test_every_parameter_appears_in_exactly_one_section():
    shown = [param.id for section in SECTIONS for param in section.fields]

    assert sorted(shown, key=lambda pid: int(pid[1:])) == list(PARAMETERS)


def test_interview_defaults_with_age_form_a_valid_consultation():
    result = validate({**INTERVIEW_DEFAULTS, "P1": "30"})

    assert result.is_valid


def test_hints_refer_to_existing_parameters():
    assert set(HINTS) <= set(PARAMETERS)
