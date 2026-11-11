import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.engine.parameters import PARAMETERS, Condition, Op, Parameter, ParamType

TOTAL_IGA_DEFICIENCY = Decimal("0.07")
BOUND_PREFIX_PARAMS = ("P3", "P5")
BOOL_VALUES = {"tak": True, "nie": False}
NUMBER = re.compile(r"-?(?:[0-9]{1,9}(?:[.,][0-9]*)?|[.,][0-9]+)")


@dataclass(frozen=True)
class Issue:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    values: dict[str, object]
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


class InvalidValue(ValueError):
    pass


def _is_missing(raw: object) -> bool:
    return raw is None or (isinstance(raw, str) and raw.strip() == "")


def _to_decimal(param: Parameter, raw: object) -> Decimal:
    if isinstance(raw, bool):
        raise InvalidValue("wymagana liczba")
    text = str(raw).strip()
    if param.id in BOUND_PREFIX_PARAMS:
        text = text.lstrip("<>").strip()
    if not NUMBER.fullmatch(text):
        raise InvalidValue("wymagana liczba")
    return Decimal(text.replace(",", "."))


def _to_int(param: Parameter, raw: object) -> int:
    number = _to_decimal(param, raw)
    if number != number.to_integral_value():
        raise InvalidValue("wymagana liczba całkowita")
    return int(number)


def _number_text(number: Decimal) -> str:
    return str(number).replace(".", ",")


def _check_range(param: Parameter, number: int | Decimal) -> None:
    if param.min is not None and number < param.min:
        raise InvalidValue(f"wartość nie może być mniejsza niż {_number_text(param.min)}")
    if param.max is not None and number > param.max:
        raise InvalidValue(f"wartość nie może być większa niż {_number_text(param.max)}")
    if param.min_exclusive is not None and number <= param.min_exclusive:
        raise InvalidValue(f"wartość musi być większa niż {_number_text(param.min_exclusive)}")


def _parse(param: Parameter, raw: object) -> object:
    if param.type is ParamType.INT:
        number = _to_int(param, raw)
        _check_range(param, number)
        return number
    if param.type is ParamType.DECIMAL:
        number = _to_decimal(param, raw)
        _check_range(param, number)
        return number
    if param.type is ParamType.ENUM:
        text = str(raw).strip()
        if text not in param.values:
            raise InvalidValue("dozwolone wartości: " + ", ".join(param.values))
        return text
    if param.type is ParamType.BOOL:
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text not in BOOL_VALUES:
            raise InvalidValue("dozwolone wartości: tak, nie")
        return BOOL_VALUES[text]
    raise TypeError(f"nieobsługiwany typ: {param.type}")


def _parse_pair(param: Parameter, raw: Mapping[str, object]) -> tuple[int, ...] | None:
    parts = [raw.get(f"{param.id}_{part}") for part in param.parts]
    if all(_is_missing(part) for part in parts):
        return None
    if any(_is_missing(part) for part in parts):
        raise InvalidValue("podaj obie liczby: " + ", ".join(param.parts))
    numbers = tuple(_to_int(param, part) for part in parts)
    for number in numbers:
        _check_range(param, number)
    return numbers


def _condition_met(condition: Condition, values: Mapping[str, object]) -> bool:
    value = values[condition.param]
    if condition.op is Op.GIVEN:
        return value is not None
    if condition.op is Op.EQ:
        return value == condition.value
    return value != condition.value


def _allowed_keys() -> set[str]:
    keys = set()
    for param in PARAMETERS.values():
        if param.type is ParamType.INT_PAIR:
            keys.update(f"{param.id}_{part}" for part in param.parts)
        else:
            keys.add(param.id)
    return keys


def validate(raw: Mapping[str, object]) -> ValidationResult:
    errors: list[Issue] = []
    warnings: list[Issue] = []

    for key in sorted(set(raw) - _allowed_keys()):
        errors.append(Issue(key, f"nieznane pole: {key}"))

    values: dict[str, object] = {}
    invalid: set[str] = set()
    for param in PARAMETERS.values():
        try:
            if param.type is ParamType.INT_PAIR:
                values[param.id] = _parse_pair(param, raw)
            elif _is_missing(raw.get(param.id)):
                values[param.id] = None
            else:
                values[param.id] = _parse(param, raw[param.id])
        except InvalidValue as error:
            values[param.id] = None
            invalid.add(param.id)
            errors.append(Issue(param.id, f"{param.label}: {error}"))

    inactive: set[str] = set()
    for param in PARAMETERS.values():
        condition = param.required_if
        if condition is not None:
            if condition.param in invalid or (
                condition.op is not Op.GIVEN and values[condition.param] is None
            ):
                continue
            if not _condition_met(condition, values):
                values[param.id] = None
                inactive.add(param.id)
                continue
        if param.id in invalid:
            continue
        if (param.required or condition is not None) and values[param.id] is None:
            errors.append(Issue(param.id, f"{param.label}: wartość wymagana"))
    errors = [issue for issue in errors if issue.field not in inactive]

    if values["P5"] is not None and values["P3"] is None and "P3" not in invalid:
        errors.append(Issue("P5", "wynik drugiej próbki wymaga wyniku pierwszego oznaczenia"))

    p3, p4, p7 = values["P3"], values["P4"], values["P7"]
    if p3 is not None and p4 is not None and p7 is not None:
        if p3 > p4 and p7 < TOTAL_IGA_DEFICIENCY:
            warnings.append(
                Issue(
                    "P3",
                    "wyniki niespójne: dodatnie anty-TG2 IgA przy IgA całkowitym < 0,07 g/L,"
                    " sprawdź wyniki",
                )
            )

    return ValidationResult(values, tuple(errors), tuple(warnings))
