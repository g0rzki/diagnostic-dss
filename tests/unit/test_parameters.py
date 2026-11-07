from app.engine.parameters import PARAMETERS, Op, ParamType


def test_registry_contains_parameters_p1_to_p17_in_order():
    assert list(PARAMETERS) == [f"P{i}" for i in range(1, 18)]


def test_registry_keys_match_parameter_ids():
    for key, param in PARAMETERS.items():
        assert key == param.id


def test_conditional_parameters_are_not_always_required():
    for param in PARAMETERS.values():
        if param.required_if is not None:
            assert not param.required


def test_conditions_refer_to_existing_parameters_and_values():
    for param in PARAMETERS.values():
        condition = param.required_if
        if condition is None:
            continue
        assert condition.param in PARAMETERS
        if condition.op in (Op.EQ, Op.NE):
            assert condition.value in PARAMETERS[condition.param].values


def test_only_enum_parameters_have_allowed_values():
    for param in PARAMETERS.values():
        assert bool(param.values) == (param.type is ParamType.ENUM)


def test_only_pair_parameters_have_parts():
    for param in PARAMETERS.values():
        assert bool(param.parts) == (param.type is ParamType.INT_PAIR)
