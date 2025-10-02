import json
import shutil
import sys
from io import StringIO
from pathlib import Path

import pytest

from Medical_KG.cli import main


@pytest.fixture()
def cli_config_dir(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[2] / "src" / "Medical_KG" / "config"
    target = tmp_path / "config"
    shutil.copytree(source, target)
    return target


@pytest.fixture(autouse=True)
def cli_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NCBI_API_KEY", "dev-ncbi")
    monkeypatch.setenv("PMC_API_KEY", "dev-pmc")
    monkeypatch.setenv("CTGOV_API_KEY", "dev-ctgov")
    monkeypatch.setenv("OPEN_FDA_API_KEY", "dev-dailymed")
    monkeypatch.setenv("CTGOV_SANDBOX_KEY", "sandbox-ctgov")
    monkeypatch.setenv("OPEN_FDA_SANDBOX_KEY", "sandbox-fda")
    monkeypatch.setenv("NEO4J_PASSWORD", "graph-password")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")


def _run_cli(args: list[str]) -> tuple[int, str]:
    buffer = StringIO()
    stdout = sys.stdout
    try:
        sys.stdout = buffer
        exit_code = main(args)
    finally:
        sys.stdout = stdout
    return exit_code, buffer.getvalue()


def test_cli_validate_success(cli_config_dir: Path) -> None:
    exit_code, output = _run_cli([
        "config",
        "validate",
        "--strict",
        "--config-dir",
        str(cli_config_dir),
    ])
    assert exit_code == 0
    assert "Config valid" in output


def test_cli_validate_failure_on_invalid_payload(cli_config_dir: Path) -> None:
    override = cli_config_dir / "config-override.yaml"
    override.write_text(
        json.dumps(
            {
                "retrieval": {
                    "fusion": {
                        "weights": {"bm25": 0.8, "splade": 0.1, "dense": 0.05}
                    }
                }
            },
            indent=2,
        )
    )
    exit_code, output = _run_cli([
        "config",
        "validate",
        "--strict",
        "--config-dir",
        str(cli_config_dir),
    ])
    assert exit_code == 1
    assert "Configuration invalid" in output


def test_cli_show_masks_secrets(cli_config_dir: Path) -> None:
    exit_code, output = _run_cli([
        "config",
        "show",
        "--config-dir",
        str(cli_config_dir),
    ])
    assert exit_code == 0
    assert "***" in output
