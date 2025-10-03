from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
from pathlib import Path

import pytest

from Medical_KG.config.manager import ConfigError, ConfigManager, mask_secrets


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[2] / "src" / "Medical_KG" / "config"
    target = tmp_path / "config"
    shutil.copytree(source, target)
    return target


@pytest.fixture()
def base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NCBI_API_KEY", "dev-ncbi")
    monkeypatch.setenv("PMC_API_KEY", "dev-pmc")
    monkeypatch.setenv("CTGOV_API_KEY", "dev-ctgov")
    monkeypatch.setenv("OPEN_FDA_API_KEY", "dev-dailymed")
    monkeypatch.setenv("CTGOV_SANDBOX_KEY", "sandbox-ctgov")
    monkeypatch.setenv("OPEN_FDA_SANDBOX_KEY", "sandbox-fda")
    monkeypatch.setenv("NEO4J_PASSWORD", "graph-password")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("PMC_STAGING_KEY", "stage-pmc")
    monkeypatch.setenv("NCBI_STAGING_KEY", "stage-ncbi")
    monkeypatch.setenv("CTGOV_STAGING_KEY", "stage-ctgov")
    monkeypatch.setenv("OPEN_FDA_STAGING_KEY", "stage-fda")
    monkeypatch.setenv("PMC_PROD_KEY", "prod-pmc")
    monkeypatch.setenv("NCBI_PROD_KEY", "prod-ncbi")
    monkeypatch.setenv("CTGOV_PROD_KEY", "prod-ctgov")
    monkeypatch.setenv("OPEN_FDA_PROD_KEY", "prod-fda")
    monkeypatch.setenv("NEO4J_PROD_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PROD_PASSWORD", "prod-password")


def test_config_loads_with_overrides_and_env(
    config_dir: Path, base_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONFIG_ENV", "dev")
    monkeypatch.setenv("LOG_LEVEL", "warn")
    override = config_dir / "config-override.yaml"
    override.write_text(
        json.dumps(
            {"retrieval": {"fusion": {"weights": {"bm25": 0.5, "splade": 0.2, "dense": 0.3}}}},
            indent=2,
        )
    )
    manager = ConfigManager(base_path=config_dir, env="dev")
    data = manager.config.data()
    assert data["observability"]["logging"]["level"] == "warn"
    assert pytest.approx(data["retrieval"]["fusion"]["weights"]["bm25"]) == 0.5
    assert manager.config.feature_flags()["extraction_experimental_enabled"] is True
    assert manager.version.raw
    assert manager.version.hash


def test_hot_reload_updates_non_breaking_fields(
    config_dir: Path, base_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONFIG_ENV", "dev")
    manager = ConfigManager(base_path=config_dir, env="dev")
    initial_version = manager.version.raw
    override = config_dir / "config-override.yaml"
    override.write_text(
        json.dumps(
            {"retrieval": {"fusion": {"weights": {"bm25": 0.6, "splade": 0.1, "dense": 0.3}}}},
            indent=2,
        )
    )
    manager.reload()
    assert manager.config.data()["retrieval"]["fusion"]["weights"]["bm25"] == pytest.approx(0.6)
    assert manager.version.raw != initial_version


def test_hot_reload_rejects_breaking_change(config_dir: Path, base_env: None) -> None:
    manager = ConfigManager(base_path=config_dir, env="dev")
    override = config_dir / "config-override.yaml"
    override.write_text(json.dumps({"embeddings": {"vllm_api_base": "https://new-host"}}, indent=2))
    with pytest.raises(ConfigError) as exc:
        manager.reload()
    assert "Breaking change requires restart" in str(exc.value)


def test_licensing_guard_blocks_unlicensed_vocab(config_dir: Path, base_env: None) -> None:
    manager = ConfigManager(base_path=config_dir, env="dev")
    override = config_dir / "config-override.yaml"
    override.write_text(
        json.dumps({"catalog": {"vocabs": {"snomed": {"enabled": True}}}}, indent=2)
    )
    with pytest.raises(ConfigError) as exc:
        manager.reload()
    assert "requires affiliate license" in str(exc.value)


def test_feature_flag_adjusts_fusion_weights(
    config_dir: Path, base_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MEDCFG__feature_flags__splade_enabled", "false")
    manager = ConfigManager(base_path=config_dir, env="dev")
    weights = manager.config.effective_fusion_weights()
    assert weights["splade"] == pytest.approx(0.0)
    assert pytest.approx(weights["bm25"] + weights["dense"]) == 1.0


def test_validate_jwt_scope(config_dir: Path, base_env: None) -> None:
    manager = ConfigManager(base_path=config_dir, env="dev")
    secret = "jwt-secret"
    auth = manager.config.auth_settings()
    payload = {
        "iss": auth.issuer,
        "aud": auth.audience,
        "scope": "admin:config other:scope",
    }
    token = _encode_jwt(payload, secret)
    claims = manager.validate_jwt(token)
    assert claims["scope"].startswith("admin:config")
    bad_token = _encode_jwt({**payload, "scope": "viewer"}, secret)
    with pytest.raises(ConfigError):
        manager.validate_jwt(bad_token)


def test_mask_secrets_masks_expected_keys() -> None:
    masked = mask_secrets(
        {
            "api_key": "${SECRET}",
            "plain": "value",
            "nested": {"password": "hunter2"},
            "list": [
                {"refresh_token": "token"},
                "value",
            ],
        }
    )
    assert masked["api_key"] == "***"
    assert masked["nested"]["password"] == "***"
    assert masked["plain"] == "value"
    assert masked["list"][0]["refresh_token"] == "***"


def test_env_override_parser_supports_json(
    config_dir: Path, base_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "RETRIEVAL_FUSION_WEIGHTS", json.dumps({"bm25": 0.7, "splade": 0.1, "dense": 0.2})
    )
    manager = ConfigManager(base_path=config_dir, env="dev")
    weights = manager.config.data()["retrieval"]["fusion"]["weights"]
    assert pytest.approx(weights["bm25"]) == 0.7
    assert pytest.approx(weights["splade"]) == 0.1
    assert pytest.approx(weights["dense"]) == 0.2


def _encode_jwt(payload: dict[str, str], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")
