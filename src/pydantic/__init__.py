"""Lightweight subset of Pydantic used for the kata test suite."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Sized,
)
from types import NoneType

try:
    from typing import Annotated
except ImportError:  # pragma: no cover
    from typing_extensions import Annotated

try:
    from types import UnionType
except ImportError:  # pragma: no cover
    UnionType = None


T = TypeVar("T")
M = TypeVar("M", bound="BaseModel")


class ValidationError(Exception):
    """Raised when validation or coercion fails."""


_MISSING = object()


@dataclass(slots=True)
class FieldInfo:
    default: Any = _MISSING
    default_factory: Callable[[], Any] | None = None
    ge: float | None = None
    gt: float | None = None
    le: float | None = None
    lt: float | None = None
    min_length: int | None = None
    alias: str | None = None
    serialization_alias: str | None = None
    discriminator: str | None = None
    description: str | None = None

    def get_default(self) -> Any:
        if self.default is not _MISSING:
            return self.default
        if self.default_factory is not None:
            return self.default_factory()
        return _MISSING


def Field(
    default: Any = _MISSING,
    *,
    default_factory: Callable[[], Any] | None = None,
    ge: float | None = None,
    gt: float | None = None,
    le: float | None = None,
    lt: float | None = None,
    min_length: int | None = None,
    alias: str | None = None,
    serialization_alias: str | None = None,
    discriminator: str | None = None,
    description: str | None = None,
) -> FieldInfo:
    return FieldInfo(
        default=default,
        default_factory=default_factory,
        ge=ge,
        gt=gt,
        le=le,
        lt=lt,
        min_length=min_length,
        alias=alias,
        serialization_alias=serialization_alias,
        discriminator=discriminator,
        description=description,
    )


def model_validator(*, mode: str = "after") -> Callable[[Callable[[M], M]], Callable[[M], M]]:
    if mode != "after":  # pragma: no cover - only mode used by tests
        raise NotImplementedError("Only mode='after' is implemented")

    def decorator(func: Callable[[M], M]) -> Callable[[M], M]:
        setattr(func, "__model_validator__", True)
        setattr(func, "__model_validator_mode__", mode)
        return func

    return decorator


def validator(
    *field_names: str,
    pre: bool = False,
    always: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            func,
            "__pydantic_validator__",
            {"fields": field_names, "pre": pre, "always": always},
        )
        return func

    return decorator


@dataclass(slots=True)
class _FieldDefinition:
    annotation: Any
    field_info: FieldInfo


class _ModelMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):
        cls = super().__new__(mcls, name, bases, dict(namespace))
        cls.__field_definitions__: Dict[str, _FieldDefinition] = {}
        cls.__field_validators__: Dict[str, list[dict[str, Any]]] = {}
        cls.__model_validators__: list[Callable[[Any], Any]] = []
        cls.__pydantic_ready__ = False
        cls.__populate_by_name__ = bool(getattr(cls, "model_config", {}).get("populate_by_name", False))
        cls.__setup_model__()
        return cls


def _unwrap_annotated(annotation: Any) -> tuple[Any, list[Any]]:
    origin = get_origin(annotation)
    if origin is Annotated:
        args = list(get_args(annotation))
        return args[0], args[1:]
    return annotation, []


class BaseModel(metaclass=_ModelMeta):
    __field_definitions__: Dict[str, _FieldDefinition]
    __field_validators__: Dict[str, list[dict[str, Any]]]
    __model_validators__: list[Callable[[Any], Any]]
    __populate_by_name__: bool

    @classmethod
    def __setup_model__(cls) -> None:
        if getattr(cls, "__pydantic_ready__", False):
            return
        hints = get_type_hints(cls, include_extras=True)
        fields: Dict[str, _FieldDefinition] = {}
        validators: Dict[str, list[dict[str, Any]]] = {}
        model_validators: list[Callable[[Any], Any]] = []

        for base in reversed(cls.__mro__[1:]):
            if hasattr(base, "__field_definitions__"):
                fields.update(getattr(base, "__field_definitions__"))
            if hasattr(base, "__field_validators__"):
                for key, funcs in getattr(base, "__field_validators__").items():
                    validators.setdefault(key, []).extend(funcs)
            if hasattr(base, "__model_validators__"):
                model_validators.extend(getattr(base, "__model_validators__"))

        for attr, value in cls.__dict__.items():
            if getattr(value, "__model_validator__", False):
                model_validators.append(value)
            validator_meta = getattr(value, "__pydantic_validator__", None)
            if validator_meta:
                for field in validator_meta["fields"]:
                    validators.setdefault(field, []).append(
                        {
                            "func": value,
                            "pre": validator_meta["pre"],
                            "always": validator_meta["always"],
                        }
                    )

        for field_name, annotation in hints.items():
            concrete_ann, metadata = _unwrap_annotated(annotation)
            field_info = FieldInfo()
            for meta in metadata:
                if isinstance(meta, FieldInfo):
                    field_info = _merge_field_info(field_info, meta)
            default_value = getattr(cls, field_name, _MISSING)
            if isinstance(default_value, FieldInfo):
                field_info = _merge_field_info(field_info, default_value)
                default_value = field_info.get_default()
            elif default_value is not _MISSING:
                field_info.default = default_value
            if default_value is _MISSING:
                if hasattr(cls, field_name):
                    delattr(cls, field_name)
            else:
                setattr(cls, field_name, default_value)
            fields[field_name] = _FieldDefinition(concrete_ann, field_info)
        cls.__field_definitions__ = fields
        cls.__field_validators__ = validators
        cls.__model_validators__ = model_validators
        cls.__pydantic_ready__ = True

    def __init__(self, **data: Any) -> None:
        self.__class__.__setup_model__()
        used: set[str] = set()
        for name, definition in self.__class__.__field_definitions__.items():
            info = definition.field_info
            alias_candidates = [name]
            if info.alias:
                alias_candidates.insert(0, info.alias)
            if self.__class__.__populate_by_name__ and info.alias:
                alias_candidates.append(info.alias)
            raw = _MISSING
            for key in alias_candidates:
                if key in data:
                    raw = data[key]
                    used.add(key)
                    break
            validators = self.__class__.__field_validators__.get(name, [])
            value = raw
            if raw is _MISSING:
                default = info.get_default()
                if default is _MISSING:
                    if any(v["always"] for v in validators if v["pre"]):
                        value = None
                    else:
                        raise ValidationError(f"Field '{name}' is required")
                else:
                    value = default
            for entry in validators:
                if entry["pre"]:
                    value = entry["func"](self.__class__, value)
            value = _coerce_value(definition.annotation, value)
            _enforce_constraints(name, value, info)
            for entry in validators:
                if not entry["pre"]:
                    value = entry["func"](self.__class__, value)
            setattr(self, name, value)
        extra = set(data.keys()) - used
        if extra:
            raise ValidationError(f"Unexpected fields: {', '.join(sorted(extra))}")
        for validator_func in self.__class__.__model_validators__:
            result = validator_func(self)
            if result not in (None, self):
                raise ValidationError("Model validators must return self or None")

    def model_dump(
        self,
        *,
        by_alias: bool = False,
        exclude_none: bool = False,
        mode: Literal["python", "json"] = "python",
    ) -> dict[str, Any]:
        if mode not in {"python", "json"}:  # pragma: no cover - defensive
            raise ValueError("mode must be 'python' or 'json'")
        output: dict[str, Any] = {}
        for name, definition in self.__class__.__field_definitions__.items():
            info = definition.field_info
            key = name
            if by_alias:
                key = info.serialization_alias or info.alias or name
            value = _to_python(getattr(self, name), by_alias=by_alias)
            if exclude_none and value is None:
                continue
            output[key] = value
        return output

    def model_dump_json(
        self,
        *,
        by_alias: bool = False,
        exclude_none: bool = False,
    ) -> str:
        return json.dumps(
            self.model_dump(by_alias=by_alias, exclude_none=exclude_none, mode="json"),
            default=_json_default,
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        params = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.__class__.__field_definitions__)
        return f"{self.__class__.__name__}({params})"

    @classmethod
    def model_validate_json(cls: Type[M], payload: str) -> M:
        data = json.loads(payload)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise ValidationError("JSON payload must decode to a dict")
        return cls(**data)

    def model_copy(self: M, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> M:
        data = self.model_dump()
        if update:
            data.update(update)
        return self.__class__(**data)


def _merge_field_info(base: FieldInfo, override: FieldInfo) -> FieldInfo:
    merged = FieldInfo(
        default=base.default,
        default_factory=base.default_factory,
        ge=base.ge,
        gt=base.gt,
        le=base.le,
        lt=base.lt,
        min_length=base.min_length,
        alias=base.alias,
        serialization_alias=base.serialization_alias,
        discriminator=base.discriminator,
        description=base.description,
    )
    if override.default is not _MISSING:
        merged.default = override.default
    if override.default_factory is not None:
        merged.default_factory = override.default_factory
    if override.ge is not None:
        merged.ge = override.ge
    if override.gt is not None:
        merged.gt = override.gt
    if override.le is not None:
        merged.le = override.le
    if override.lt is not None:
        merged.lt = override.lt
    if override.min_length is not None:
        merged.min_length = override.min_length
    if override.alias is not None:
        merged.alias = override.alias
    if override.serialization_alias is not None:
        merged.serialization_alias = override.serialization_alias
    if override.discriminator is not None:
        merged.discriminator = override.discriminator
    if override.description is not None:
        merged.description = override.description
    if override.default is _MISSING and override.default_factory is None:
        if base.default is not _MISSING:
            merged.default = base.default
        if base.default_factory is not None:
            merged.default_factory = base.default_factory
    return merged


def _enforce_constraints(name: str, value: Any, info: FieldInfo) -> None:
    if isinstance(value, (int, float)):
        if info.gt is not None and not value > info.gt:
            raise ValidationError(f"Field '{name}' must be > {info.gt}")
        if info.ge is not None and value < info.ge:
            raise ValidationError(f"Field '{name}' must be >= {info.ge}")
        if info.lt is not None and not value < info.lt:
            raise ValidationError(f"Field '{name}' must be < {info.lt}")
        if info.le is not None and value > info.le:
            raise ValidationError(f"Field '{name}' must be <= {info.le}")
    if info.min_length is not None:
        if not isinstance(value, Sized):
            candidate = _iterable(value)
            if candidate is None:
                raise ValidationError(
                    f"Field '{name}' must be sized to enforce min_length"
                )
            value = tuple(candidate)
        if len(value) < info.min_length:
            raise ValidationError(f"Field '{name}' must have length >= {info.min_length}")


def _to_python(value: Any, *, by_alias: bool) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=by_alias)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_to_python(item, by_alias=by_alias) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_python(item, by_alias=by_alias) for item in value)
    if isinstance(value, dict):
        return {key: _to_python(val, by_alias=by_alias) for key, val in value.items()}
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return value.model_dump()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serialisable")


def _coerce_value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            if issubclass(annotation, Enum):
                if isinstance(value, annotation):
                    return value
                return annotation(value)
            if issubclass(annotation, BaseModel):
                if isinstance(value, annotation):
                    return value
                if isinstance(value, Mapping):
                    return annotation(**value)
            if annotation in (int, float, str, bool):
                return annotation(value)
        return value
    if origin in (list, Sequence, Iterable):
        args = get_args(annotation)
        item_type = args[0] if args else Any
        iterator = _iterable(value)
        if iterator is None:
            raise ValidationError("Value is not iterable")
        return [_coerce_value(item_type, item) for item in iterator]
    if origin is Literal:
        choices = get_args(annotation)
        if not choices:
            return value
        target = choices[0]
        if isinstance(target, Enum):
            enum_type = target.__class__
            if isinstance(value, enum_type):
                return value
            return enum_type(value)
        return value
    if origin in (tuple,):  # pragma: no cover - unused
        args = get_args(annotation)
        return tuple(_coerce_value(args[0], item) for item in value)
    if origin in (dict, Mapping, MutableMapping):
        key_type, val_type = get_args(annotation) if get_args(annotation) else (Any, Any)
        return {
            _coerce_value(key_type, key): _coerce_value(val_type, val) for key, val in value.items()
        }
    if origin in (Union, UnionType):
        for arg in get_args(annotation):
            if arg is NoneType:
                if value is None:
                    return None
                continue
            try:
                return _coerce_value(arg, value)
            except Exception:
                continue
        return value
    if origin is Optional:
        inner = get_args(annotation)[0]
        return _coerce_value(inner, value)
    return value


class TypeAdapter:
    """Minimal discriminated union adapter supporting Field(discriminator=...)."""

    def __init__(self, type_: Any) -> None:
        inner, metadata = _unwrap_annotated(type_)
        self._discriminator: str | None = None
        for meta in metadata:
            if isinstance(meta, FieldInfo) and meta.discriminator:
                self._discriminator = meta.discriminator
        origin = get_origin(inner)
        if origin not in (Union, UnionType):
            raise TypeError("TypeAdapter currently only supports unions")
        self._choices = list(get_args(inner))

    def _match_choice(self, data: Mapping[str, Any]) -> Type[Any]:
        if self._discriminator is None:
            raise ValidationError("Discriminator required for union validation")
        if self._discriminator not in data:
            raise ValidationError(f"Missing discriminator '{self._discriminator}'")
        discriminator_value = data[self._discriminator]
        for choice in self._choices:
            if not issubclass(choice, BaseModel):
                continue
            expected = getattr(choice, self._discriminator, None)
            if isinstance(expected, Enum):
                expected_value = expected.value
            else:
                expected_value = expected
            if discriminator_value == expected_value:
                return choice
            if isinstance(expected, Enum) and isinstance(discriminator_value, str):
                try:
                    if expected == expected.__class__(discriminator_value):
                        return choice
                except Exception:  # pragma: no cover
                    continue
        raise ValidationError(
            f"No matching choice for discriminator '{self._discriminator}' with value {discriminator_value!r}"
        )

    def validate_python(self, data: Mapping[str, Any]) -> Any:
        model_type = self._match_choice(data)
        return model_type(**data)

    def dump_python(self, value: Any, *, by_alias: bool = False) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(by_alias=by_alias)
        raise ValidationError("Unsupported value for dump_python")


__all__ = [
    "BaseModel",
    "Field",
    "FieldInfo",
    "TypeAdapter",
    "ValidationError",
    "model_validator",
    "validator",
]
