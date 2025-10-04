from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import yaml
from Medical_KG.config import manager as config_manager
from Medical_KG.config.manager import ConfigError, ConfigManager, ConfigSchemaValidator


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
    monkeypatch.setenv("NEO4J_PASSWORD", "graph-password")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")


def _load_payload(config_dir: Path) -> dict[str, object]:
    payload = yaml.safe_load((config_dir / "config.yaml").read_text())
    assert isinstance(payload, dict)
    return payload


def test_validator_caches_compiled_schema(
    config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_path = config_dir / "config.schema.json"
    monkeypatch.setattr(config_manager, "_SCHEMA_CACHE", {})
    monkeypatch.setattr(config_manager, "_PATH_DIGEST", {})
    first = ConfigSchemaValidator(schema_path)
    cache_size = len(config_manager._SCHEMA_CACHE)
    second = ConfigSchemaValidator(schema_path)
    assert len(config_manager._SCHEMA_CACHE) == cache_size == 1
    assert first._schema_key == second._schema_key


def test_validator_emits_color_sequences(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate({"config_version": "1.0.0"}, source="unit-test", use_color=True)
    assert "\x1b[" in str(exc.value)


def test_one_of_accepts_weights_profile(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    fusion = payload["retrieval"]["fusion"]
    fusion.pop("weights")
    fusion["weights_profile"] = "balanced"
    validator = ConfigSchemaValidator(schema_path)
    validator.validate(payload)


def test_one_of_rejects_multiple_weight_sources(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    payload["retrieval"]["fusion"]["weights_profile"] = "balanced"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "oneOf" in str(exc.value)


def test_any_of_requires_matching_credentials(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    source = payload["sources"]["pubmed"]
    source.pop("api_key", None)
    source["client_id"] = "pubmed-client"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "client_secret" in str(exc.value)
    source["client_secret"] = "pubmed-secret"
    validator.validate(payload)


def test_custom_formats_guard_urls_and_paths(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    payload["embeddings"]["vllm_api_base"] = "ftp://invalid.example.com"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "format 'url_with_scheme'" in str(exc.value)

    payload = _load_payload(config_dir)
    payload["licensing"]["policy_path"] = "missing.yaml"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "format 'file_path'" in str(exc.value)


def test_migration_adds_missing_fields(config_dir: Path, base_env: None) -> None:
    manager = ConfigManager(base_path=config_dir, env="dev")
    payload = _load_payload(config_dir)
    payload.pop("feature_flags", None)
    payload.setdefault("observability", {}).setdefault("logging", {})["level"] = "debug"
    migrated, steps = manager.migrate(payload, target_version="1.0.0")
    assert migrated["feature_flags"]["splade_enabled"] is False
    assert migrated["observability"]["logging"]["level"] == "DEBUG"
    assert any(step.startswith("update-$schema") for step in steps)


def test_staging_config_migrates_cleanly(config_dir: Path) -> None:
    secrets = {
        "NCBI_STAGING_KEY": "ncbi-staging",
        "PMC_STAGING_KEY": "pmc-staging",
        "CTGOV_STAGING_KEY": "ctgov-staging",
        "OPEN_FDA_STAGING_KEY": "openfda-staging",
    }
    resolver = config_manager.SecretResolver(env=secrets)
    manager = ConfigManager(base_path=config_dir, env="staging", secret_resolver=resolver)
    migrated, steps = manager.migrate(target_version="1.0.0")
    assert migrated["$schema_version"] == "1.0.0"
    assert migrated["feature_flags"]["extraction_experimental_enabled"] is False
    assert any(step.startswith("set-$schema") or step.startswith("update-$schema") for step in steps)


def test_validate_one_thousand_payloads(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    baseline = _load_payload(config_dir)
    for index in range(1000):
        payload = deepcopy(baseline)
        payload["config_version"] = f"1.0.0+{index}"
        validator.validate(payload)


def test_all_environment_configs_validate(config_dir: Path, base_env: None) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    for name in [
        "config.yaml",
        "config-dev.yaml",
        "config-staging.yaml",
        "config-prod.yaml",
    ]:
        payload = yaml.safe_load((config_dir / name).read_text()) or {}
        assert isinstance(payload, dict)
        validator.validate(payload, source=name)


def test_validator_accepts_current_configuration_snapshot(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    payload = _load_payload(config_dir)
    validator.validate(payload, source="unit-test")

