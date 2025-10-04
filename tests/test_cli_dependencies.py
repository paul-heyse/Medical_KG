from __future__ import annotations

import json
from typing import Iterable

import pytest

from Medical_KG.cli import main
from Medical_KG.utils.optional_dependencies import DependencyStatus


def _fake_statuses() -> Iterable[DependencyStatus]:
    return [
        DependencyStatus(
            feature_name="observability",
            packages=("prometheus-client",),
            extras_group="observability",
            installed=True,
            missing_packages=(),
            install_hint="pip install medical-kg[observability]",
            docs_url="docs/dependencies.md#observability",
        ),
        DependencyStatus(
            feature_name="http",
            packages=("httpx",),
            extras_group="http",
            installed=False,
            missing_packages=("httpx",),
            install_hint="pip install medical-kg[http]",
            docs_url="docs/dependencies.md#http-clients",
        ),
    ]


def test_dependencies_check_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("Medical_KG.cli.iter_dependency_statuses", lambda: _fake_statuses())
    exit_code = main(["dependencies", "check", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload[1]["feature"] == "http"
    assert payload[1]["installed"] is False
    assert payload[1]["install_hint"] == "pip install medical-kg[http]"


def test_dependencies_check_text_verbose(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("Medical_KG.cli.iter_dependency_statuses", lambda: _fake_statuses())
    exit_code = main(["dependencies", "check", "--verbose"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "observability [observability]: installed" in output
    assert "http [http]: missing" in output
    assert "install: pip install medical-kg[http]" in output
    assert "docs: docs/dependencies.md#observability" in output
