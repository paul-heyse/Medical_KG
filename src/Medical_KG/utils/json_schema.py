"""Reusable JSON schema validation helpers with rich error reporting."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Sequence

from jsonschema import FormatChecker, ValidationError
from jsonschema.validators import validator_for


class JsonSchemaValidationError(RuntimeError):
    """Raised when JSON schema validation fails."""

    def __init__(self, heading: str, messages: Sequence[str]) -> None:
        self.heading = heading
        self.messages = tuple(messages)
        message = heading if not messages else heading + "\n" + "\n\n".join(messages)
        super().__init__(message)


_DEFAULT_REQUIRED_PATTERN = re.compile(r"'(?P<field>[^']+)' is a required property")


def pointer_from_path(path: Iterable[Any]) -> str:
    parts = [str(part) for part in path]
    if not parts:
        return "<root>"
    return "/" + "/".join(parts)


def stringify_instance(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def default_expected_description(error: ValidationError) -> str | None:
    validator = error.validator
    data = error.validator_value
    if validator == "type":
        if isinstance(data, Iterable):
            return " or ".join(str(item) for item in data)
        return str(data)
    if validator == "enum" and isinstance(data, Iterable):
        return "one of " + ", ".join(str(item) for item in data)
    if validator in {"minimum", "exclusiveMinimum"}:
        comparator = ">=" if validator == "minimum" else ">"
        return f"{comparator} {data}"
    if validator in {"maximum", "exclusiveMaximum"}:
        comparator = "<=" if validator == "maximum" else "<"
        return f"{comparator} {data}"
    if validator in {"minItems", "maxItems"}:
        comparator = ">=" if validator == "minItems" else "<="
        return f"array length {comparator} {data}"
    if validator == "required":
        match = _DEFAULT_REQUIRED_PATTERN.search(error.message)
        if match:
            return f"required property '{match.group('field')}'"
    if validator == "additionalProperties":
        return "only declared properties"
    if validator == "format" and isinstance(error.schema, Mapping):
        fmt = error.schema.get("format")
        if isinstance(fmt, str):
            return f"format '{fmt}'"
    return None


def default_remediation_hint(error: ValidationError) -> str | None:
    validator = error.validator
    if validator == "enum" and isinstance(error.validator_value, Iterable):
        options = ", ".join(str(item) for item in error.validator_value)
        return f"Choose one of: {options}."
    if validator == "type":
        expected = error.validator_value
        if isinstance(expected, Iterable):
            expected = ", ".join(str(item) for item in expected)
        return f"Provide a value of type {expected}."
    if validator in {"minimum", "exclusiveMinimum"}:
        return f"Increase the value to at least {error.validator_value}."
    if validator in {"maximum", "exclusiveMaximum"}:
        return f"Reduce the value to at most {error.validator_value}."
    if validator == "required":
        match = _DEFAULT_REQUIRED_PATTERN.search(error.message)
        if match:
            return f"Add the missing '{match.group('field')}' property."
    if validator == "additionalProperties":
        return "Remove unexpected properties or update the schema."
    return None


def default_format_error(error: ValidationError, source: str) -> str:
    pointer = pointer_from_path(error.absolute_path)
    value_repr = stringify_instance(error.instance)
    expected = default_expected_description(error)
    hint = default_remediation_hint(error)
    lines = [
        f"{source} -> {pointer}",
        f"  Problem: {error.message}",
        f"  Value: {value_repr}",
    ]
    if expected:
        lines.append(f"  Expected: {expected}")
    if hint:
        lines.append(f"  Hint: {hint}")
    return "\n".join(lines)


class JsonSchemaValidator:
    """Adapter exposing ``validate`` with formatted error output."""

    def __init__(
        self,
        schema: Mapping[str, Any],
        *,
        heading: str = "Schema validation failed:",
        format_checker: FormatChecker | None = None,
        formatter: Callable[[ValidationError, str], str] | None = None,
    ) -> None:
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        self._validator = validator_cls(schema, format_checker=format_checker)
        self._heading = heading
        self._formatter = formatter or default_format_error

    def validate(self, payload: Mapping[str, Any], *, source: str) -> None:
        errors = sorted(
            self._validator.iter_errors(payload),
            key=lambda err: tuple(str(part) for part in err.absolute_path),
        )
        if not errors:
            return
        messages = [self._formatter(error, source) for error in errors]
        raise JsonSchemaValidationError(self._heading, messages)


__all__ = [
    "JsonSchemaValidationError",
    "JsonSchemaValidator",
    "default_expected_description",
    "default_format_error",
    "default_remediation_hint",
    "pointer_from_path",
    "stringify_instance",
]
