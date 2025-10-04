from typing import Any
import logging

class JsonFormatter(logging.Formatter):
    def __init__(self, fmt: str | None = ..., *, rename_fields: dict[str, str] | None = ..., json_default: Any | None = ..., json_encoder: type[Any] | None = ..., json_serializer: Any | None = ..., prefix: str | None = ..., json_indent: int | None = ..., ensure_ascii: bool = ..., mix_extra: bool = ..., timestamp: bool = ..., json_kwargs: dict[str, Any] | None = ...) -> None: ...

    def add_fields(self, log_record: dict[str, Any], record: Any, message_dict: dict[str, Any]) -> None: ...

    def process_log_record(self, log_record: dict[str, Any]) -> dict[str, Any]: ...

__all__ = ["JsonFormatter"]
