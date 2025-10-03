from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Iterable, Mapping, Protocol, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class HTTPException(Exception):
    status_code: int
    detail: Any
    headers: Dict[str, str]

    def __init__(self, *, status_code: int, detail: Any, headers: Mapping[str, str] | None = ...) -> None: ...

class Request:
    scope: Mapping[str, Any]
    method: str
    url: str
    headers: Dict[str, str]
    path_params: Dict[str, str]

    def __init__(self, scope: Mapping[str, Any], body: bytes, headers: Mapping[str, str]) -> None: ...

    async def body(self) -> bytes: ...

class Response:
    status_code: int
    headers: Dict[str, str]
    body: bytes

    def __init__(self, *, status_code: int = ..., headers: Mapping[str, str] | None = ...) -> None: ...

class DependsMarker(Protocol[T]):
    dependency: Callable[..., Awaitable[T] | T]

class HeaderInfo:
    alias: str | None
    default: Any

def Depends(dependency: Callable[..., Awaitable[T] | T]) -> DependsMarker[T]: ...

def Header(default: Any = ..., *, alias: str | None = ...) -> HeaderInfo: ...

class APIRouter:
    prefix: str
    tags: Sequence[str]

    def __init__(self, *, prefix: str = ..., tags: Sequence[str] | None = ...) -> None: ...

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Awaitable[Any] | Any],
        *,
        methods: Iterable[str],
        response_model: type[BaseModel] | None = ..., 
        **kwargs: Any,
    ) -> None: ...

    def get(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = ..., 
        tags: Sequence[str] | None = ..., 
        **kwargs: Any,
    ) -> Callable[[Callable[..., Awaitable[Any] | Any]], Callable[..., Awaitable[Any] | Any]]: ...

    def post(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = ..., 
        tags: Sequence[str] | None = ..., 
        **kwargs: Any,
    ) -> Callable[[Callable[..., Awaitable[Any] | Any]], Callable[..., Awaitable[Any] | Any]]: ...

class HTTPAuthorizationCredentials:
    scheme: str
    credentials: str

class HTTPBearer:
    def __init__(self, *, auto_error: bool = ...) -> None: ...

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None: ...

class status:
    HTTP_200_OK: int
    HTTP_201_CREATED: int
    HTTP_204_NO_CONTENT: int
    HTTP_400_BAD_REQUEST: int
    HTTP_401_UNAUTHORIZED: int
    HTTP_403_FORBIDDEN: int
    HTTP_404_NOT_FOUND: int
    HTTP_409_CONFLICT: int
    HTTP_422_UNPROCESSABLE_ENTITY: int
    HTTP_429_TOO_MANY_REQUESTS: int

__all__ = [
    "APIRouter",
    "Depends",
    "DependsMarker",
    "Header",
    "HeaderInfo",
    "HTTPAuthorizationCredentials",
    "HTTPBearer",
    "HTTPException",
    "Request",
    "Response",
    "status",
]
