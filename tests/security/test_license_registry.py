from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from Medical_KG.security import LicenseRegistry

from .fixtures import write_license_file


def _registry(tmp_path) -> LicenseRegistry:
    return LicenseRegistry.from_yaml(write_license_file(tmp_path))


def test_free_tier_blocks_and_redacts(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session(
        "free", expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    with pytest.raises(PermissionError):
        session.enforce_feature("briefing")

    redacted = session.filter_label("SNOMED", "Heart failure")
    assert redacted == "[upgrade-required]"

    session.record_usage("requests_per_day", 5)
    with pytest.raises(PermissionError):
        session.record_usage("requests_per_day", 6)

    assert registry.filter_labels("UNKNOWN", "free", "X") == "[unavailable]"


def test_basic_tier_partial_access(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("basic")

    session.enforce_feature("briefing")
    with pytest.raises(PermissionError):
        session.enforce_feature("kg-write")

    assert session.filter_label("SNOMED", "Term") == "Term"
    assert "upgrade" in session.filter_label("MEDDRA", "AE")


def test_pro_tier_expanded_limits(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("pro")
    session.enforce_feature("kg-write")
    assert session.record_usage("requests_per_day", 999) == 999
    session.record_usage("requests_per_day", 1)


def test_enterprise_tier_full_access(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("enterprise")
    session.enforce_feature("briefing")
    session.enforce_feature("kg-write")
    assert session.filter_label("LOINC", "1234-5") == "1234-5"
    assert session.record_usage("requests_per_day", 100) == 100


def test_upgrade_and_downgrade(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("free")
    with pytest.raises(PermissionError):
        session.enforce_feature("briefing")

    session.upgrade("pro")
    session.enforce_feature("briefing")
    session.record_usage("requests_per_day", 100)

    session.downgrade("basic")
    with pytest.raises(PermissionError):
        session.enforce_feature("kg-write")
    with pytest.raises(PermissionError):
        session.record_usage("requests_per_day", 950)


def test_feature_overrides(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("basic")
    session.set_override("kg-write", True)
    session.enforce_feature("kg-write")
    session.set_override("briefing", False)
    with pytest.raises(PermissionError):
        session.enforce_feature("briefing")


def test_license_expiration_with_grace(tmp_path) -> None:
    registry = _registry(tmp_path)
    now = datetime.now(timezone.utc)
    session = registry.create_session("basic", expires_at=now - timedelta(days=1))
    # within grace period of 3 days defined in fixtures
    session.enforce_feature("briefing")
    future = now + timedelta(days=5)
    with pytest.raises(PermissionError):
        session.enforce_feature("briefing", now=future)


def test_require_raises_for_unlicensed(tmp_path) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(PermissionError):
        registry.require("MEDDRA")


def test_usage_negative_rejected(tmp_path) -> None:
    registry = _registry(tmp_path)
    session = registry.create_session("basic")
    with pytest.raises(ValueError):
        session.record_usage("requests_per_day", -1)


def test_unknown_tier_and_filter_denied(tmp_path) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(KeyError):
        registry.get_tier("unknown")

    label = registry.filter_labels("SNOMED", "free", "term")
    assert "cannot access" in label
    assert registry.filter_labels("MEDDRA", "basic", "term") == "[license required]"


def test_registry_parses_optional_sections(tmp_path) -> None:
    custom = tmp_path / "custom.yml"
    custom.write_text(
        """
vocabs:
  test:
    licensed: true
tiers:
  limited:
    features: null
    usage_limits: null
    redactions:
      test: '"quoted"'
""",
        encoding="utf-8",
    )
    registry = LicenseRegistry.from_yaml(custom)
    assert "limited" in registry.available_tiers()
    tier = registry.get_tier("limited")
    assert tier.redactions["TEST"] == "quoted"
    assert registry.filter_labels("TEST", "limited", "label") == "label"
