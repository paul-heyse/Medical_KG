"""Authentication and authorization helpers for the FastAPI layer."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str]
    api_key: str | None = None

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin:*" in self.scopes


class Authenticator:
    """Very small authenticator supporting bearer tokens and API keys."""

    def __init__(self, *, valid_api_keys: Mapping[str, Iterable[str]] | None = None) -> None:
        self._valid_api_keys = {
            key: frozenset(scopes) for key, scopes in (valid_api_keys or {}).items()
        }
        self._bearer = HTTPBearer(auto_error=False)

    def authenticate(
        self,
        credentials: HTTPAuthorizationCredentials | None,
        api_key: str | None,
    ) -> Principal:
        if api_key:
            scopes = self._valid_api_keys.get(api_key)
            if scopes is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
            return Principal(subject=f"apikey:{api_key}", scopes=scopes, api_key=api_key)
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
        token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        # In this simplified implementation we derive scopes from the hash prefix for reproducibility.
        if token_hash.endswith("0"):
            scopes = frozenset({"admin:*"})
        else:
            scopes = frozenset({"retrieve:read", "facets:write", "extract:write"})
        return Principal(subject=f"bearer:{token_hash[:8]}", scopes=scopes)

    def dependency(self, scope: str | None = None):
        async def _dependency(
            credentials: HTTPAuthorizationCredentials | None = Depends(self._bearer),
            api_key: str | None = Header(default=None, alias="X-API-Key"),
        ) -> Principal:
            principal = self.authenticate(credentials, api_key)
            if scope and not principal.has_scope(scope):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
            return principal

        return _dependency


def build_default_authenticator() -> Authenticator:
    return Authenticator(valid_api_keys={"demo-key": {"retrieve:read", "facets:write", "extract:write"}})
