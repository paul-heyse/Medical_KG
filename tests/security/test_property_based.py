from __future__ import annotations

from datetime import datetime, timedelta, timezone

import hypothesis.strategies as st
from hypothesis import given

import pytest

from Medical_KG.security.licenses import LicenseEntry, LicenseRegistry, LicenseSession, LicenseTier
from Medical_KG.security.rbac import RBACEngine, Role
from Medical_KG.security.retention import PurgePipeline, RetentionPolicy, RetentionRecord


@st.composite
def license_config(draw) -> tuple[LicenseRegistry, LicenseSession, dict[str, int]]:
    features = draw(st.dictionaries(st.text(min_size=1, max_size=5), st.booleans(), min_size=1, max_size=4))
    limits = draw(st.dictionaries(st.text(min_size=1, max_size=5), st.integers(min_value=1, max_value=5), min_size=1, max_size=3))
    tier = LicenseTier(
        name="dynamic",
        can_access={"VOCAB": True},
        features=features,
        usage_limits=limits,
        redactions={},
        grace_period_days=0,
    )
    registry = LicenseRegistry(entries={"VOCAB": LicenseEntry("VOCAB", True, None)}, tiers={"dynamic": tier})
    session = registry.create_session("dynamic")
    return registry, session, limits


@given(license_config())
def test_usage_limits_respected(config: tuple[LicenseRegistry, LicenseSession, dict[str, int]]) -> None:
    _, session, limits = config
    for metric, limit in limits.items():
        session.record_usage(metric, limit)
        with pytest.raises(PermissionError):
            session.record_usage(metric, 1)


@given(st.lists(st.sampled_from(["viewer", "editor", "admin"]), min_size=1, max_size=3))
def test_role_hierarchy_inheritance(role_names: list[str]) -> None:
    roles = {
        "viewer": Role(name="viewer", allow=frozenset({"read"})),
        "editor": Role(name="editor", allow=frozenset({"read", "write"}), parents=("viewer",)),
        "admin": Role(name="admin", allow=frozenset({"read", "write", "delete"}), parents=("editor",), deny=frozenset({"delete"})),
    }
    engine = RBACEngine(roles)
    engine.assign("user", *role_names)
    allowed, _ = engine.permissions_for("user")
    if "admin" in (name.lower() for name in role_names):
        assert "write" in allowed
        assert "delete" not in allowed
    elif "editor" in (name.lower() for name in role_names):
        assert allowed == frozenset({"read", "write"})
    else:
        assert allowed == frozenset({"read"})


@given(
    st.integers(min_value=1, max_value=365),
    st.integers(min_value=1, max_value=400),
    st.booleans(),
)
def test_retention_policy_safety(retention_days: int, age_days: int, dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    record = RetentionRecord(doc_id="doc", created_at=now - timedelta(days=age_days), data={"pii": "value"}, tags=())
    pipeline = PurgePipeline({}, {}, {}, {}, {})
    policy = RetentionPolicy(name="test", retention_days=retention_days, anonymize_fields=("pii",), dry_run=dry_run)
    result = policy.execute([record], pipeline, now=now)
    if age_days > retention_days and not dry_run:
        assert result.deleted == ("doc",)
        assert record.data["pii"] == "[anonymized]"
    elif dry_run and age_days > retention_days:
        assert result.dry_run_report == ("doc",)
    else:
        assert result.skipped == ("doc",)
