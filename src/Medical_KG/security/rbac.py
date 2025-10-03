"""Scope and role-based access control utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence


class ScopeError(PermissionError):
    """Raised when a request lacks required scopes."""


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    allow: frozenset[str]
    deny: frozenset[str] = frozenset()
    parents: tuple[str, ...] = ()
    scope: frozenset[str] = frozenset()


class ScopeEnforcer:
    def __init__(self, required_scopes: Sequence[str]) -> None:
        self._required = set(required_scopes)

    def verify(self, provided: Iterable[str]) -> None:
        provided_set = set(provided)
        missing = self._required - provided_set
        if missing:
            raise ScopeError(f"Missing scopes: {', '.join(sorted(missing))}")


class RBACEngine:
    """Resolves hierarchical roles and evaluates permissions."""

    def __init__(self, roles: Mapping[str, Role]) -> None:
        self._roles = {role_name.lower(): role for role_name, role in roles.items()}
        self._assignments: MutableMapping[str, set[str]] = {}

    def assign(self, user_id: str, *role_names: str) -> None:
        assigned = self._assignments.setdefault(user_id, set())
        for name in role_names:
            normalized = name.lower()
            if normalized not in self._roles:
                raise KeyError(f"Unknown role {name}")
            assigned.add(normalized)

    def revoke(self, user_id: str, role_name: str) -> None:
        if user_id not in self._assignments:
            return
        self._assignments[user_id].discard(role_name.lower())

    def permissions_for(self, user_id: str) -> tuple[frozenset[str], frozenset[str]]:
        role_names = self._assignments.get(user_id, set())
        allowed: set[str] = set()
        denied: set[str] = set()
        scopes: set[str] = set()
        for role_name in role_names:
            self._expand_role(role_name, allowed, denied, scopes)
        return frozenset(allowed - denied), frozenset(scopes)

    def check_permission(
        self,
        user_id: str,
        permission: str,
        *,
        required_scope: str | None = None,
    ) -> None:
        allowed, scopes = self.permissions_for(user_id)
        if permission not in allowed:
            raise PermissionError(f"User {user_id} lacks permission {permission}")
        if required_scope and required_scope not in scopes:
            raise ScopeError(f"Missing scope {required_scope}")

    def _expand_role(
        self, role_name: str, allowed: set[str], denied: set[str], scopes: set[str]
    ) -> None:
        role = self._roles.get(role_name)
        if role is None:
            raise KeyError(f"Unknown role {role_name}")
        allowed.update(role.allow)
        denied.update(role.deny)
        scopes.update(role.scope)
        for parent in role.parents:
            self._expand_role(parent.lower(), allowed, denied, scopes)


__all__ = ["ScopeEnforcer", "ScopeError", "Role", "RBACEngine"]
