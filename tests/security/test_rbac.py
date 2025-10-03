from __future__ import annotations

import pytest

from Medical_KG.security import RBACEngine, Role, ScopeEnforcer, ScopeError

from .fixtures import sample_users


def _engine() -> RBACEngine:
    roles = {
        "viewer": Role(name="viewer", allow=frozenset({"read"}), scope=frozenset({"reports"})),
        "analyst": Role(
            name="analyst",
            allow=frozenset({"read", "write"}),
            parents=("viewer",),
            scope=frozenset({"reports", "analytics"}),
        ),
        "admin": Role(
            name="admin",
            allow=frozenset({"read", "write", "delete"}),
            deny=frozenset({"delete:audit"}),
            parents=("analyst",),
            scope=frozenset({"*"}),
        ),
    }
    return RBACEngine(roles)


def test_role_assignment_and_permissions() -> None:
    engine = _engine()
    for user in sample_users():
        engine.assign(user.user_id, *user.roles)
    allowed, scopes = engine.permissions_for("alice")
    assert "read" in allowed
    assert "reports" in scopes


def test_permission_checks_with_hierarchy() -> None:
    engine = _engine()
    engine.assign("bob", "analyst")
    engine.check_permission("bob", "write", required_scope="analytics")
    with pytest.raises(PermissionError):
        engine.check_permission("bob", "delete")


def test_admin_conflicting_permissions() -> None:
    engine = _engine()
    engine.assign("carol", "admin")
    engine.check_permission("carol", "delete")
    with pytest.raises(PermissionError):
        engine.check_permission("carol", "delete:audit")


def test_role_revocation() -> None:
    engine = _engine()
    engine.assign("dave", "viewer")
    engine.revoke("dave", "viewer")
    with pytest.raises(PermissionError):
        engine.check_permission("dave", "read")


def test_scope_enforcer() -> None:
    enforcer = ScopeEnforcer(["admin", "metrics"])
    enforcer.verify(["admin", "metrics", "other"])
    with pytest.raises(PermissionError):
        enforcer.verify(["admin"])


def test_unknown_role_errors() -> None:
    engine = _engine()
    engine.revoke("ghost", "viewer")
    with pytest.raises(KeyError):
        engine.assign("user", "missing")
    engine.assign("user", "viewer")
    engine.revoke("user", "viewer")
    with pytest.raises(PermissionError):
        engine.check_permission("user", "read")
    engine.assign("scoped", "viewer")
    with pytest.raises(ScopeError):
        engine.check_permission("scoped", "read", required_scope="analytics")


def test_broken_parent_role() -> None:
    roles = {"broken": Role(name="broken", allow=frozenset(), parents=("missing",))}
    engine = RBACEngine(roles)
    engine.assign("user", "broken")
    with pytest.raises(KeyError):
        engine.permissions_for("user")
