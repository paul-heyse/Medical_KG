"""FastAPI application exposing configuration hot-reload endpoint."""

from __future__ import annotations

from typing import Annotated, Awaitable, Callable, TYPE_CHECKING, cast
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from Medical_KG.api.routes import ApiRouter
from Medical_KG.briefing import router as briefing_router
from Medical_KG.config.manager import ConfigError, ConfigManager
from Medical_KG.observability import configure_logging, setup_tracing
from Medical_KG.retrieval import RetrievalService, create_router
from Medical_KG.api.types import FastAPIApp

if TYPE_CHECKING:  # pragma: no cover - typing only
    def _FastAPIFactory(*args: object, **kwargs: object) -> FastAPIApp:
        ...

else:  # pragma: no cover - runtime import
    from fastapi import FastAPI as _FastAPIFactory

_security = HTTPBearer(auto_error=False)


def create_app(
    manager: ConfigManager | None = None,
    retrieval_service: RetrievalService | None = None,
) -> FastAPIApp:
    configure_logging()
    manager = manager or ConfigManager()
    app: FastAPIApp = _FastAPIFactory(title="Medical KG", version=manager.version.raw)

    # Setup API router
    api_router = ApiRouter()
    app.include_router(api_router)
    app.state.api_router = api_router

    # Setup retrieval service if provided
    if retrieval_service is not None:
        app.include_router(create_router(retrieval_service))

    setup_tracing(app)

    middleware_decorator = cast(
        Callable[
            [Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]],
            Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]],
        ],
        app.middleware("http"),
    )

    @middleware_decorator
    async def add_request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        traceparent = request.headers.get("traceparent")
        response = await call_next(request)
        response.headers.setdefault("x-request-id", request_id)
        if traceparent:
            response.headers.setdefault("traceparent", traceparent)
        return response

    reload_decorator = cast(
        Callable[[Callable[..., Awaitable[dict[str, str]]]], Callable[..., Awaitable[dict[str, str]]]],
        app.post("/admin/reload", tags=["admin"], summary="Hot reload configuration"),
    )

    @reload_decorator
    async def reload_config(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_security)
        ],
    ) -> dict[str, str]:
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
