"""FastAPI application exposing configuration hot-reload endpoint."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from Medical_KG.briefing import router as briefing_router
from Medical_KG.config.manager import ConfigError, ConfigManager
from Medical_KG.retrieval import RetrievalService, create_router

_security = HTTPBearer(auto_error=False)


def create_app(
    manager: ConfigManager | None = None,
    retrieval_service: RetrievalService | None = None,
) -> FastAPI:
    manager = manager or ConfigManager()
    app = FastAPI(title="Medical KG", version=manager.version.raw)

    if retrieval_service is not None:
        app.include_router(create_router(retrieval_service))

    @app.post("/admin/reload", tags=["admin"], summary="Hot reload configuration")
    async def reload_config(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> dict:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
            )
        token = credentials.credentials
        try:
            manager.validate_jwt(token)
            manager.reload()
        except ConfigError as exc:
            message = str(exc)
            lowered = message.lower()
            if (
                "token" in lowered
                or "scope" in lowered
                or "issuer" in lowered
                or "audience" in lowered
            ):
                status_code = status.HTTP_403_FORBIDDEN
            else:
                status_code = status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"config_version": manager.version.raw, "hash": manager.version.hash}

    app.include_router(briefing_router)

    return app


__all__ = ["create_app"]
