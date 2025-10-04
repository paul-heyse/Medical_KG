from __future__ import annotations

import importlib
import importlib.util
from typing import Any

import pytest

from Medical_KG.utils.optional_dependencies import (
    DependencyStatus,
    MissingDependencyError,
    iter_dependency_statuses,
    optional_import,
)


def test_optional_import_raises_missing_dependency_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = importlib.import_module

    def fake_import(name: str, package: str | None = None) -> Any:
        if name in {"fakepkg", "custompkg"}:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    with pytest.raises(MissingDependencyError) as excinfo:
        optional_import("fakepkg", feature_name="observability", package_name="fakepkg")
    message = str(excinfo.value)
    assert "Feature 'observability'" in message
    assert "pip install medical-kg[observability]" in message

    with pytest.raises(MissingDependencyError) as custom_exc:
        optional_import(
            "custompkg",
            feature_name="custom",
            package_name="custompkg",
            extras_group="custom-extra",
            docs_url="https://example.invalid/deps#custom",
        )
    custom_message = str(custom_exc.value)
    assert "Feature 'custom'" in custom_message
    assert "pip install medical-kg[custom-extra]" in custom_message
    assert "https://example.invalid/deps#custom" in custom_message


def test_dependency_status_reports_missing_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str) -> Any:
        if name == "httpx":
            return None
        return original_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    statuses = {status.feature_name: status for status in iter_dependency_statuses()}
    http_status = statuses["http"]
    assert not http_status.installed
    assert http_status.missing_packages == ("httpx",)
    assert http_status.install_hint == "pip install medical-kg[http]"
    assert http_status.docs_url is not None


def test_dependency_status_dataclass_roundtrip() -> None:
    status = DependencyStatus(
        feature_name="demo",
        packages=("pkg",),
        extras_group="demo",
        installed=True,
        missing_packages=(),
        install_hint="pip install medical-kg[demo]",
        docs_url="docs/dependencies.md#demo",
    )
    assert status.feature_name == "demo"
    assert status.installed is True
    assert status.missing_packages == ()
