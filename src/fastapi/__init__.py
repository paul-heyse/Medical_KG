from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, get_type_hints

from pydantic import BaseModel

from . import status  # noqa: E402  # re-exported


class HTTPException(Exception):
    def __init__(self, *, status_code: int, detail: Any, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
        self.headers = dict(headers or {})


class HeaderInfo:
    def __init__(self, default: Any = None, *, alias: str | None = None) -> None:
        self.default = default
        self.alias = alias


class DependsMarker:
    def __init__(self, dependency: Callable[..., Any]) -> None:
        self.dependency = dependency

    async def resolve(self, request: "Request", response: "Response") -> Any:
        return await _call_with_injection(self.dependency, request, response, {})


def Depends(dependency: Callable[..., Any]) -> DependsMarker:
    return DependsMarker(dependency)


def Header(default: Any = None, *, alias: str | None = None) -> HeaderInfo:
    return HeaderInfo(default=default, alias=alias)


class Request:
    def __init__(self, scope: Mapping[str, Any], body: bytes, headers: Mapping[str, str]) -> None:
        self.scope = scope
        self.method = scope.get("method", "GET").upper()
        self.url = f"{scope.get('scheme', 'http')}://{scope.get('server', ('testserver', 80))[0]}{scope.get('path', '/')}"
        self.path_params: Dict[str, str] = {}
        self._body = body
        self._json_cache: Any = ...
        self.headers = {key.lower(): value for key, value in headers.items()}

    async def body(self) -> bytes:
        return self._body

    async def json(self) -> Any:
        if self._json_cache is ...:
            if not self._body:
                self._json_cache = {}
            else:
                text = self._body.decode("utf-8")
                if not text:
                    self._json_cache = {}
                else:
                    self._json_cache = json.loads(text)
        return self._json_cache


class Response:
    def __init__(self, *, status_code: int = status.HTTP_200_OK, headers: Mapping[str, str] | None = None) -> None:
        self.status_code = status_code
        self.headers: Dict[str, str] = dict(headers or {})
        self.body: bytes = b""

    def set_body(self, content: bytes) -> None:
        self.body = content


@dataclass
class _Route:
    path: str
    methods: Sequence[str]
    endpoint: Callable[..., Any]
    response_model: type[BaseModel] | None = None

    def __post_init__(self) -> None:
        self.methods = [method.upper() for method in self.methods]
        self._parts: List[tuple[str, str]] = []
        segments = [segment for segment in self.path.strip("/").split("/") if segment]
        if self.path == "/":
            segments = []
        for segment in segments:
            if segment.startswith("{") and segment.endswith("}"):
                name = segment[1:-1]
                self._parts.append(("param", name))
            else:
                self._parts.append(("literal", segment))

    def match(self, method: str, path: str) -> Dict[str, str] | None:
        if method.upper() not in self.methods:
            return None
        path_segments = [segment for segment in path.strip("/").split("/") if segment]
        if path == "/":
            path_segments = []
        if len(path_segments) != len(self._parts):
            return None
        params: Dict[str, str] = {}
        for (kind, value), segment in zip(self._parts, path_segments):
            if kind == "literal" and value != segment:
                return None
            if kind == "param":
                params[value] = segment
        return params

    async def handle(self, request: Request, response: Response, path_params: Dict[str, str]) -> Any:
        return await _call_with_injection(self.endpoint, request, response, path_params)


class APIRouter:
    def __init__(self, *, prefix: str = "", tags: Sequence[str] | None = None) -> None:
        self.routes: List[_Route] = []
        self.prefix = prefix.rstrip("/")
        self.tags = list(tags or [])

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Iterable[str],
        response_model: type[BaseModel] | None = None,
        **_: Any,
    ) -> None:
        full_path = self._join_path(path)
        self.routes.append(
            _Route(path=full_path, methods=list(methods), endpoint=endpoint, response_model=response_model)
        )

    def get(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = None,
        tags: Sequence[str] | None = None,
        **_: Any,
    ):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, methods=["GET"], response_model=response_model)
            return func

        return decorator

    def post(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = None,
        tags: Sequence[str] | None = None,
        **_: Any,
    ):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, methods=["POST"], response_model=response_model)
            return func

        return decorator

    def _join_path(self, path: str) -> str:
        if not path:
            return self.prefix or "/"
        if path == "/":
            return self.prefix or "/"
        if self.prefix:
            return f"{self.prefix}{path if path.startswith('/') else '/' + path}"
        return path


class FastAPI:
    def __init__(self, *, title: str, version: str) -> None:
        self.title = title
        self.version = version
        self.state = SimpleNamespace()
        self._routes: List[_Route] = []
        self._middleware: List[Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]] = []

    def include_router(self, router: APIRouter) -> None:
        self._routes.extend(router.routes)

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Iterable[str],
        response_model: type[BaseModel] | None = None,
        **_: Any,
    ) -> None:
        self._routes.append(_Route(path=path, methods=list(methods), endpoint=endpoint, response_model=response_model))

    def get(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = None,
        tags: Sequence[str] | None = None,
        **_: Any,
    ):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, methods=["GET"], response_model=response_model)
            return func

        return decorator

    def post(
        self,
        path: str,
        *,
        response_model: type[BaseModel] | None = None,
        tags: Sequence[str] | None = None,
        **_: Any,
    ):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, methods=["POST"], response_model=response_model)
            return func

        return decorator

    def middleware(self, kind: str) -> Callable[[Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]], Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]]:
        if kind != "http":  # pragma: no cover - only http supported
            raise NotImplementedError("Only HTTP middleware is supported")

        def decorator(func: Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]):
            self._middleware.append(func)
            return func

        return decorator

    def include_router_with_state(self, router: APIRouter, attribute: str) -> None:
        setattr(self.state, attribute, router)
        self.include_router(router)

    async def __call__(self, scope: Mapping[str, Any], receive: Callable[[], Awaitable[Mapping[str, Any]]], send: Callable[[Mapping[str, Any]], Awaitable[None]]) -> None:
        if scope.get("type") != "http":  # pragma: no cover - http only
            return
        body = await _consume_body(receive)
        headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in scope.get("headers", [])}
        request = Request(scope, body, headers)

        async def call_endpoint(req: Request) -> Response:
            return await self._dispatch(req)

        handler = call_endpoint
        for middleware in reversed(self._middleware):
            previous = handler

            async def wrapper(req: Request, middleware=middleware, previous=previous) -> Response:
                return await middleware(req, previous)

            handler = wrapper

        try:
            response = await handler(request)
        except HTTPException as exc:
            response = Response(status_code=exc.status_code, headers=exc.headers)
            payload = json.dumps({"detail": exc.detail}).encode("utf-8")
            response.set_body(payload)
            response.headers.setdefault("content-type", "application/json")
        await send({
            "type": "http.response.start",
            "status": response.status_code,
            "headers": [(name.encode("latin-1"), value.encode("latin-1")) for name, value in response.headers.items()],
        })
        await send({"type": "http.response.body", "body": response.body, "more_body": False})

    async def _dispatch(self, request: Request) -> Response:
        for route in self._routes:
            path_params = route.match(request.method, request.scope.get("path", "/"))
            if path_params is None:
                continue
            request.path_params = path_params
            response = Response()
            result = await route.handle(request, response, path_params)
            if isinstance(result, Response):
                return result
            payload = _render_response(result)
            response.set_body(payload)
            response.headers.setdefault("content-type", "application/json")
            return response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def _consume_body(receive: Callable[[], Awaitable[Mapping[str, Any]]]) -> bytes:
    body = bytearray()
    while True:
        message = await receive()
        body.extend(message.get("body", b""))
        if not message.get("more_body"):
            break
    return bytes(body)


async def _call_with_injection(
    func: Callable[..., Any],
    request: Request,
    response: Response,
    path_params: Mapping[str, str],
) -> Any:
    signature = inspect.signature(func)
    kwargs: Dict[str, Any] = {}
    body_data: Any = ...
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:  # pragma: no cover - fallback
        hints = {}
    for name, parameter in signature.parameters.items():
        annotation = hints.get(name, parameter.annotation)
        default = parameter.default
        if annotation is Request or annotation == Request or annotation == "Request":
            kwargs[name] = request
            continue
        if annotation is Response or annotation == Response or annotation == "Response":
            kwargs[name] = response
            continue
        if isinstance(default, DependsMarker):
            kwargs[name] = await default.resolve(request, response)
            continue
        if isinstance(default, HeaderInfo):
            header_name = (default.alias or name).replace("_", "-")
            kwargs[name] = request.headers.get(header_name.lower(), default.default)
            continue
        if name in path_params:
            kwargs[name] = _convert_type(annotation, path_params[name])
            continue
        if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
            if body_data is ...:
                body_data = await request.json()
            kwargs[name] = annotation(**body_data)
            continue
        if body_data is ...:
            body_data = await request.json()
        value = body_data.get(name)
        if value is None and default is not inspect._empty:
            value = default
        kwargs[name] = value
    result = func(**kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


def _convert_type(annotation: Any, value: str) -> Any:
    if annotation in (inspect._empty, str, Any):
        return value
    try:
        if annotation is int:
            return int(value)
        if annotation is float:
            return float(value)
    except ValueError:
        return value
    return value


def _render_response(result: Any) -> bytes:
    if result is None:
        return b""
    if isinstance(result, Response):
        return result.body
    if isinstance(result, BaseModel):
        return result.model_dump_json().encode("utf-8")
    if isinstance(result, (dict, list)):
        return json.dumps(result).encode("utf-8")
    if isinstance(result, str):
        return result.encode("utf-8")
    return json.dumps(result).encode("utf-8")


__all__ = [
    "APIRouter",
    "Depends",
    "FastAPI",
    "Header",
    "HTTPException",
    "Request",
    "Response",
    "status",
]
