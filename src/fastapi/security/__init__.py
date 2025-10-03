from __future__ import annotations

from dataclasses import dataclass

from .. import HTTPException, Request, status


@dataclass
class HTTPAuthorizationCredentials:
    scheme: str
    credentials: str


class HTTPBearer:
    def __init__(self, *, auto_error: bool = True) -> None:
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        if request is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            return None
        header = request.headers.get("authorization")
        if not header:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            return None
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                )
            return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)


__all__ = ["HTTPBearer", "HTTPAuthorizationCredentials"]
