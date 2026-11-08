from decimal import Decimal
from itertools import product

import pytest

from app.engine.derived import COMPUTE, DERIVED
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


def facts(**changes):
    values = dict.fromkeys(PARAMETERS)
    values.update(P1=30, P2="normalne", P9="nie wykonano", P10=False, P11=False, P12="nie omówiono")
    values.update(P13="nie wykonano", P15="nie badano", P17=False)
    values.update(changes)
    return values


@pytest.mark.parametrize(
    "result, expected", [(None, "brak"), ("9", "ujemny"), ("10", "ujemny"), ("11", "dodatni")]
)
def test_d1_result_equal_to_limit_is_negative(result, expected):
    value = None if result is None else Decimal(result)
    assert COMPUTE["D1"](facts(P3=value, P4=Decimal(10) if value else None)) == expected


@pytest.mark.parametrize("result, expected", [("99.9", False), ("100", True), ("0.7", True)])
def test_d2_high_titre_starts_at_ten_times_limit(result, expected):
    limit = Decimal("0.07") if result == "0.7" else Decimal(10)
    assert COMPUTE["D2"](facts(P3=Decimal(result), P4=limit)) is expected


def test_second_sample_values_use_second_limit():
    values = facts(P3=Decimal(100), P4=Decimal(10), P5=Decimal(50), P6=Decimal(10))

    assert COMPUTE["D1_2"](values) == "dodatni"
    assert COMPUTE["D2_2"](values) is False


@pytest.mark.parametrize(
    "iga, expected",
    [(None, "brak"), ("0.069", "całkowity"), ("0.07", "częściowy"), ("0.69", "częściowy")]
    + [("0.7", "norma")],
)
def test_d3_iga_categories(iga, expected):
    value = None if iga is None else Decimal(iga)
    assert COMPUTE["D3"](facts(P7=value, P8=Decimal("0.7") if value else None)) == expected


def high_titre(**changes):
    return facts(P3=Decimal(150), P4=Decimal(10), **changes)


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, True),
        ({"P1": 44}, True),
        ({"P1": 45}, False),
        ({"P11": True}, False),
        ({"P2": "ograniczone", "P16": False}, False),
        ({"P13": "0", "P14": (4, 1)}, False),
        ({"P7": Decimal("0.05"), "P8": Decimal("0.7")}, False),
        ({"P7": Decimal("0.5"), "P8": Decimal("0.7")}, True),
        ({"P15": "ujemny"}, False),
        ({"P15": "dodatni"}, True),
    ],
)
def test_d4_no_biopsy_path_conditions(changes, expected):
    assert COMPUTE["D4"](high_titre(**changes)) is expected


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({"P3": Decimal(20), "P4": Decimal(10)}, "dodatnia"),
        ({"P9": "dodatni"}, "dodatnia"),
        (
            {"P3": Decimal(20), "P4": Decimal(10), "P7": Decimal("0.05"), "P8": Decimal("0.7")},
            "nieustalona",
        ),
        ({"P3": Decimal(5), "P4": Decimal(10), "P7": Decimal(1), "P8": Decimal("0.7")}, "ujemna"),
        ({"P3": Decimal(5), "P4": Decimal(10)}, "nieustalona"),
        (
            {"P3": Decimal(5), "P4": Decimal(10), "P7": Decimal("0.5"), "P8": Decimal("0.7")},
            "nieustalona",
        ),
        (
            {"P3": Decimal(5), "P4": Decimal(10), "P7": Decimal("0.5"), "P8": Decimal("0.7")}
            | {"P9": "ujemny"},
            "ujemna",
        ),
        ({"P7": Decimal("0.05"), "P8": Decimal("0.7"), "P9": "ujemny"}, "ujemna"),
        ({"P7": Decimal("0.05"), "P8": Decimal("0.7")}, "nieustalona"),
    ],
)
def test_d5_specific_serology_status(changes, expected):
    assert COMPUTE["D5"](facts(**changes)) == expected


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({"P3": Decimal(50), "P4": Decimal(10)}, True),
        ({"P3": Decimal(100), "P4": Decimal(10)}, False),
        ({"P3": Decimal(10), "P4": Decimal(10)}, False),
        (
            {"P3": Decimal(50), "P4": Decimal(10), "P7": Decimal("0.05"), "P8": Decimal("0.7")},
            False,
        ),
    ],
)
def test_d6_low_titre(changes, expected):
    assert COMPUTE["D6"](facts(**changes)) is expected


@pytest.mark.parametrize(
    "biopsies, expected", [(None, False), ((4, 1), True), ((3, 2), False), ((4, 0), False)]
)
def test_d7_enough_biopsies(biopsies, expected):
    assert COMPUTE["D7"](facts(P14=biopsies)) is expected


@pytest.mark.parametrize(
    "diet, challenge, expected",
    [("normalne", None, True), ("ograniczone", False, False), ("ograniczone", True, True)],
)
def test_d8_gluten_sufficient(diet, challenge, expected):
    assert COMPUTE["D8"](facts(P2=diet, P16=challenge)) is expected


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, True),
        ({"P12": "tak"}, True),
        ({"P12": "nie"}, False),
        ({"P12": "tak", "P5": Decimal(50), "P6": Decimal(10)}, True),
        ({"P12": "tak", "P5": Decimal(5), "P6": Decimal(10)}, False),
        ({"P1": 50}, False),
    ],
)
def test_d9_no_biopsy_path_in_progress(changes, expected):
    assert COMPUTE["D9"](high_titre(**changes)) is expected


class RecordingValues(dict):
    def __init__(self, values):
        super().__init__(values)
        self.read = set()

    def __getitem__(self, key):
        self.read.add(key)
        return super().__getitem__(key)


def sample_states():
    antibodies = [(None, None), (Decimal(5), Decimal(10)), (Decimal(50), Decimal(10))]
    antibodies.append((Decimal(150), Decimal(10)))
    iga = [(None, None), (Decimal("0.05"), Decimal("0.7")), (Decimal("0.5"), Decimal("0.7"))]
    iga.append((Decimal(1), Decimal("0.7")))
    histology = [("nie wykonano", None), ("0", (4, 1)), ("1", (3, 1))]
    diet = [("normalne", None), ("ograniczone", False), ("ograniczone", True)]
    for (p3, p4), (p5, p6), (p7, p8), (p13, p14), (p2, p16), p1, p9, p11, p12, p15 in product(
        antibodies,
        antibodies,
        iga,
        histology,
        diet,
        (30, 50),
        ("dodatni", "ujemny", "nie wykonano"),
        (True, False),
        ("nie omówiono", "tak", "nie"),
        ("dodatni", "ujemny", "nie badano"),
    ):
        if p3 is None and p5 is not None:
            continue
        yield facts(
            P1=p1, P2=p2, P3=p3, P4=p4, P5=p5, P6=p6, P7=p7, P8=p8, P9=p9, P11=p11, P12=p12
        ) | {"P13": p13, "P14": p14, "P15": p15, "P16": p16}


def test_each_derived_value_reads_exactly_its_declared_parameters():
    read = {key: set() for key in COMPUTE}
    for state in sample_states():
        for key, compute in COMPUTE.items():
            values = RecordingValues(state)
            compute(values)
            assert values.read <= set(DERIVED[key].reads), key
            read[key] |= values.read

    assert read == {key: set(DERIVED[key].reads) for key in COMPUTE}


def test_every_registered_derived_value_has_a_computation():
    assert list(COMPUTE) == list(DERIVED)
