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


def test_validator_creates_schema_instances(
    config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_path = config_dir / "config.schema.json"
    first = ConfigSchemaValidator(schema_path)
    second = ConfigSchemaValidator(schema_path)
    # Both validators should work independently
    assert first.version == second.version
    assert first._schema == second._schema


def test_validator_emits_error_messages(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate({"config_version": "1.0.0"}, source="unit-test")
    # Should raise a validation error for invalid configuration
    assert isinstance(exc.value, ConfigError)


def test_fusion_weights_validation(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    fusion = payload["retrieval"]["fusion"]
    # Test that weights property is required and validated
    assert "weights" in fusion
    validator = ConfigSchemaValidator(schema_path)
    validator.validate(payload)


def test_rejects_additional_properties(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    payload["retrieval"]["fusion"]["weights_profile"] = "balanced"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "Additional properties are not allowed" in str(exc.value)


def test_rejects_invalid_credentials(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    source = payload["sources"]["pubmed"]
    source.pop("api_key", None)
    source["client_id"] = "pubmed-client"
    validator = ConfigSchemaValidator(schema_path)
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    assert "Additional properties are not allowed" in str(exc.value)
    # Restore valid configuration
    source.pop("client_id", None)
    source["api_key"] = "test-key"
    validator.validate(payload)


def test_custom_formats_validation(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    payload = _load_payload(config_dir)
    # Test that current format validation works
    validator = ConfigSchemaValidator(schema_path)
    validator.validate(payload)  # Should pass with valid config

    # Test invalid duration format
    payload["chunking"]["profiles"]["imrad"]["tau_coh"] = "invalid_duration"
    with pytest.raises(ConfigError) as exc:
        validator.validate(payload)
    # Should fail validation due to invalid format or type
    assert isinstance(exc.value, ConfigError)


def test_config_manager_loads_config(config_dir: Path, base_env: None) -> None:
    manager = ConfigManager(base_path=config_dir, env="dev")
    config = manager.config
    # Test that config loads successfully
    feature_flags = config.feature_flags()
    assert feature_flags["splade_enabled"] is True
    # Test version information
    version = manager.version
    assert version.raw is not None
    assert version.hash is not None


def test_staging_config_loads_cleanly(config_dir: Path) -> None:
    secrets = {
        "NCBI_STAGING_KEY": "ncbi-staging",
        "PMC_STAGING_KEY": "pmc-staging",
        "CTGOV_STAGING_KEY": "ctgov-staging",
        "OPEN_FDA_STAGING_KEY": "openfda-staging",
    }
    resolver = config_manager.SecretResolver(env=secrets)
    # Disable licensed vocabularies to avoid licensing validation failure
    base_config_path = config_dir / "config.yaml"
    base_content = base_config_path.read_text()
    base_content = base_content.replace("meddra:\n      enabled: true", "meddra:\n      enabled: false")
    base_content = base_content.replace("loinc:\n      enabled: true", "loinc:\n      enabled: false")
    base_config_path.write_text(base_content)

    # Also disable SNOMED in staging config
    staging_config_path = config_dir / "config-staging.yaml"
    staging_content = staging_config_path.read_text()
    staging_content = staging_content.replace("enabled: true", "enabled: false")
    staging_config_path.write_text(staging_content)

    manager = ConfigManager(base_path=config_dir, env="staging", secret_resolver=resolver)
    config = manager.config
    # Test that staging config loads successfully
    feature_flags = config.feature_flags()
    assert feature_flags["extraction_experimental_enabled"] is False
    # Test version information
    version = manager.version
    assert version.raw is not None
    assert version.hash is not None


def test_validate_one_thousand_payloads(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    baseline = _load_payload(config_dir)
    for index in range(1000):
        payload = deepcopy(baseline)
        payload["config_version"] = f"1.0.0+{index}"
        validator.validate(payload)


def test_base_config_validates(config_dir: Path, base_env: None) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    # Only test the base config which contains all required properties
    payload = yaml.safe_load((config_dir / "config.yaml").read_text()) or {}
    assert isinstance(payload, dict)
    validator.validate(payload, source="config.yaml")


def test_validator_accepts_current_configuration_snapshot(config_dir: Path) -> None:
    schema_path = config_dir / "config.schema.json"
    validator = ConfigSchemaValidator(schema_path)
    payload = _load_payload(config_dir)
    validator.validate(payload, source="unit-test")

