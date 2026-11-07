from app.engine.derived import DERIVED
from app.engine.parameters import PARAMETERS, ParamType


def test_registry_contains_catalog_definitions_and_second_sample_variants():
    assert list(DERIVED) == ["D1", "D1_2", "D2", "D2_2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]


def test_registry_keys_match_derived_ids():
    for key, derived in DERIVED.items():
        assert key == derived.id


def test_derived_values_read_existing_parameters_only():
    for derived in DERIVED.values():
        assert derived.reads
        assert set(derived.reads) <= set(PARAMETERS)


def test_derived_values_are_choices_or_yes_no():
    for derived in DERIVED.values():
        assert derived.type in (ParamType.ENUM, ParamType.BOOL)
        assert bool(derived.values) == (derived.type is ParamType.ENUM)


def test_derived_ids_do_not_clash_with_parameter_ids():
    assert not set(DERIVED) & set(PARAMETERS)
