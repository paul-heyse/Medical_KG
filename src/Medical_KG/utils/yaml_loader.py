"""Shared YAML loading utilities with deterministic type semantics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO, Any, TextIO

import yaml


class YamlLoaderError(RuntimeError):
    """Raised when YAML payloads cannot be loaded as the expected structure."""


def load_yaml_data(
    source: str | Path | TextIO | IO[str],
    *,
    description: str | None = None,
) -> Any:
    """Load a YAML document from ``source`` and normalise container types."""

    text = _read_source(source, description=description)
    try:
        loaded = yaml.safe_load(text)
    except Exception as exc:  # pragma: no cover - delegated to yaml
        raise YamlLoaderError(_format_message("Failed to parse", description, exc)) from exc
    if loaded is None:
        return {}
    return _to_builtin(loaded)


def load_yaml_mapping(
    source: str | Path | TextIO | IO[str],
    *,
    description: str | None = None,
) -> dict[str, Any]:
    """Load a YAML mapping from ``source`` returning plain ``dict`` values."""

    loaded = load_yaml_data(source, description=description)
    if isinstance(loaded, Mapping):
        return {str(key): value for key, value in loaded.items()}
    raise YamlLoaderError(
        _format_message(
            "Expected YAML mapping",
            description,
            f"got {type(loaded).__name__}",
        )
    )


def _read_source(
    source: str | Path | TextIO | IO[str],
    *,
    description: str | None,
) -> str:
    if isinstance(source, Path):
        try:
            return source.read_text(encoding="utf-8")
        except OSError as exc:
            raise YamlLoaderError(
                _format_message("Failed to read", description, exc)
            ) from exc
    if hasattr(source, "read"):
        try:
            return str(source.read())
        except OSError as exc:  # pragma: no cover - file-like read errors
            raise YamlLoaderError(
                _format_message("Failed to read", description, exc)
            ) from exc
    if isinstance(source, (bytes, bytearray)):
        return source.decode("utf-8")
    return str(source)


def _to_builtin(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_builtin(val) for key, val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_builtin(item) for item in value]
    return value


def _format_message(prefix: str, description: str | None, detail: object) -> str:
    label = description or "YAML payload"
    return f"{prefix} {label}: {detail}"


__all__ = ["YamlLoaderError", "load_yaml_data", "load_yaml_mapping"]
