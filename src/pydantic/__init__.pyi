from __future__ import annotations

from typing import Any, Callable, Dict, Generic, Iterable, Mapping, Sequence, Type, TypeVar

T = TypeVar("T")
M = TypeVar("M", bound="BaseModel")

class ValidationError(Exception):
    ...

class FieldInfo:
    default: Any
    default_factory: Callable[[], Any] | None
    ge: float | None
    gt: float | None
    le: float | None
    lt: float | None
    min_length: int | None
    alias: str | None
    serialization_alias: str | None
    discriminator: str | None
    description: str | None

    def get_default(self) -> Any: ...

class ConfigDict(Dict[str, Any]):
    ...

def Field(
    default: Any = ...,
    *,
    default_factory: Callable[[], Any] | None = ...,
    ge: float | None = ...,
    gt: float | None = ...,
    le: float | None = ...,
    lt: float | None = ...,
    min_length: int | None = ...,
    alias: str | None = ...,
    serialization_alias: str | None = ...,
    discriminator: str | None = ...,
    description: str | None = ...,
) -> FieldInfo: ...

def model_validator(*, mode: str = ...) -> Callable[[Callable[[M], M]], Callable[[M], M]]: ...

def validator(
    *field_names: str,
    pre: bool = ...,
    always: bool = ...,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...

class BaseModel:
    model_config: Dict[str, Any]

    def __init__(self, **data: Any) -> None: ...

    @classmethod
    def model_validate_json(cls: Type[M], json_data: str) -> M: ...

    @classmethod
    def model_validate(cls: Type[M], data: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> M: ...

    def model_dump(self, *, mode: str | None = ...) -> Dict[str, Any]: ...

    def model_dump_json(self, *, mode: str | None = ...) -> str: ...

    def model_copy(self: M, *, update: Mapping[str, Any] | None = ..., deep: bool = ...) -> M: ...

class TypeAdapter(Generic[T]):
    def __init__(self, type_: Type[T]) -> None: ...

    def validate_python(self, value: Any) -> T: ...

__all__ = [
    "BaseModel",
    "ConfigDict",
    "Field",
    "FieldInfo",
    "TypeAdapter",
    "ValidationError",
    "model_validator",
    "validator",
]
