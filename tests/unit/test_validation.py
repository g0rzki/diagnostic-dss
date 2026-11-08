from decimal import Decimal

import pytest

from app.engine.validation import validate

BASE_FORM = {
    "P1": "30",
    "P2": "normalne",
    "P9": "nie wykonano",
    "P10": "nie",
    "P11": "nie",
    "P12": "nie omówiono",
    "P13": "nie wykonano",
    "P15": "nie badano",
    "P17": "nie",
}


def form(**changes):
    return {**BASE_FORM, **changes}


def error_fields(result):
    return [issue.field for issue in result.errors]


def test_interview_only_form_is_valid():
    result = validate(BASE_FORM)

    assert result.is_valid
    assert result.warnings == ()
    assert result.values["P1"] == 30
    assert result.values["P10"] is False
    assert result.values["P3"] is None
    assert result.values["P14"] is None


@pytest.mark.parametrize("age, valid", [("17", False), ("18", True), ("120", True), ("121", False)])
def test_age_range_is_18_to_120(age, valid):
    assert validate(form(P1=age)).is_valid is valid


@pytest.mark.parametrize("age", ["abc", "30,5", "30.5", True, "NaN", "Infinity"])
def test_age_must_be_an_integer(age):
    assert error_fields(validate(form(P1=age))) == ["P1"]


def test_decimal_comma_and_dot_are_accepted():
    result = validate(form(P3="12,5", P4="10.0"))

    assert result.values["P3"] == Decimal("12.5")
    assert result.values["P4"] == Decimal("10")


def test_float_input_keeps_exact_decimal_value():
    result = validate(form(P3=0.7, P4=0.07))

    assert result.values["P4"] == Decimal("0.07")
    assert result.values["P3"] >= 10 * result.values["P4"]


@pytest.mark.parametrize("field", ["P3", "P4", "P5", "P6"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_antibody_values_must_be_positive(field, value):
    changes = {"P3": "20", "P4": "10", "P5": "20", "P6": "10", field: value}

    assert error_fields(validate(form(**changes))) == [field]


def test_total_iga_may_be_zero():
    assert validate(form(P7="0", P8="0,7")).is_valid


def test_total_iga_must_not_be_negative():
    assert error_fields(validate(form(P7="-0,1", P8="0,7"))) == ["P7"]


@pytest.mark.parametrize("limit, valid", [("0,07", False), ("0,08", True)])
def test_iga_lower_limit_must_exceed_0_07(limit, valid):
    assert validate(form(P7="1", P8=limit)).is_valid is valid


@pytest.mark.parametrize("raw, expected", [("< 5", "5"), (">200", "200")])
def test_lab_bound_prefix_is_stripped_for_antibody_results(raw, expected):
    result = validate(form(P3=raw, P4="10", P5=raw, P6="10"))

    assert result.values["P3"] == Decimal(expected)
    assert result.values["P5"] == Decimal(expected)


def test_range_message_uses_decimal_comma():
    result = validate(form(P7="1", P8="0,07"))

    assert [issue.message for issue in result.errors] == [
        "dolna granica normy IgA całkowitego: wartość musi być większa niż 0,07"
    ]


def test_lab_bound_prefix_is_rejected_for_total_iga():
    assert error_fields(validate(form(P7="< 0,07", P8="0,7"))) == ["P7"]


@pytest.mark.parametrize("field", ["P2", "P9", "P12", "P13", "P15"])
def test_choice_outside_allowed_values_is_rejected(field):
    assert error_fields(validate(form(**{field: "inna"}))) == [field]


@pytest.mark.parametrize("raw, expected", [("tak", True), ("NIE", False), (True, True)])
def test_yes_no_values_are_converted_to_bool(raw, expected):
    assert validate(form(P17=raw)).values["P17"] is expected


def test_yes_no_value_outside_tak_nie_is_rejected():
    assert error_fields(validate(form(P17="yes"))) == ["P17"]


@pytest.mark.parametrize("field", ["P1", "P2", "P9", "P10", "P11", "P12", "P13", "P15", "P17"])
def test_missing_required_field_is_rejected(field):
    data = form(**{field: ""})

    assert error_fields(validate(data)) == [field]


@pytest.mark.parametrize("given, required", [("P3", "P4"), ("P5", "P6"), ("P7", "P8")])
def test_value_requires_its_reference_limit(given, required):
    changes = {"P3": "20", "P4": "10", given: "5"}
    changes.pop(required, None)

    assert error_fields(validate(form(**changes))) == [required]


def test_biopsy_counts_are_required_after_histology():
    assert error_fields(validate(form(P13="2"))) == ["P14"]


def test_biopsy_counts_are_converted_to_pair():
    result = validate(form(P13="2", P14_dalsza="4", P14_opuszka="1"))

    assert result.is_valid
    assert result.values["P14"] == (4, 1)


def test_single_biopsy_count_is_rejected():
    assert error_fields(validate(form(P13="2", P14_dalsza="4"))) == ["P14"]


def test_negative_biopsy_count_is_rejected():
    assert error_fields(validate(form(P13="2", P14_dalsza="-1", P14_opuszka="1"))) == ["P14"]


def test_biopsy_counts_are_dropped_without_histology():
    result = validate(form(P14_dalsza="4", P14_opuszka="1"))

    assert result.is_valid
    assert result.values["P14"] is None


def test_gluten_challenge_is_required_on_restricted_diet():
    assert error_fields(validate(form(P2="ograniczone"))) == ["P16"]


def test_gluten_challenge_is_dropped_on_normal_diet():
    result = validate(form(P16="tak"))

    assert result.is_valid
    assert result.values["P16"] is None


def test_second_sample_without_first_result_is_rejected():
    assert error_fields(validate(form(P5="20", P6="10"))) == ["P5"]


def test_unknown_field_is_rejected():
    assert error_fields(validate(form(P18="tak"))) == ["P18"]


def test_all_errors_are_reported_together():
    assert error_fields(validate(form(P1="", P2="inna"))) == ["P2", "P1"]


def test_positive_iga_antibody_with_total_iga_deficiency_gives_warning():
    result = validate(form(P3="20", P4="10", P7="0,05", P8="0,7"))

    assert result.is_valid
    assert [issue.field for issue in result.warnings] == ["P3"]


def test_antibody_equal_to_limit_with_total_iga_deficiency_gives_no_warning():
    result = validate(form(P3="10", P4="10", P7="0,05", P8="0,7"))

    assert result.warnings == ()
