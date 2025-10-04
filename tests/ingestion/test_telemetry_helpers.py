from __future__ import annotations

import logging
from typing import Any

import pytest

from Medical_KG.ingestion.telemetry import (
    CompositeTelemetry,
    HttpBackoffEvent,
    HttpErrorEvent,
    HttpRequestEvent,
    HttpResponseEvent,
    HttpRetryEvent,
    LoggingTelemetry,
    PrometheusTelemetry,
    TracingTelemetry,
    generate_request_id,
)


def test_logging_telemetry_emits_structured_payload(caplog: pytest.LogCaptureFixture) -> None:
    telemetry = LoggingTelemetry(logger=logging.getLogger("test.telemetry"))
    event = HttpRequestEvent(
        request_id=generate_request_id(),
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.0,
        headers={"Authorization": "secret"},
    )

    with caplog.at_level(logging.INFO):
        telemetry.on_request(event)

    assert caplog.records
    record = caplog.records[0]
    assert record.message == "http.request"
    assert record.http_event["method"] == "GET"
    assert record.http_event["headers"]["Authorization"] == "<redacted>"


def test_composite_telemetry_routes_by_host() -> None:
    calls: list[tuple[str, str]] = []

    class _Telemetry:
        def __init__(self, name: str) -> None:
            self._name = name

        def on_request(self, event: HttpRequestEvent) -> None:
            calls.append((self._name, event.host))

    composite = CompositeTelemetry(
        _Telemetry("global"),
        per_host={"example.com": [_Telemetry("host")], "other.com": [_Telemetry("other")]},
    )

    request = HttpRequestEvent(
        request_id=generate_request_id(),
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.0,
        headers={},
    )
    composite.on_request(request)

    other_request = HttpRequestEvent(
        request_id=generate_request_id(),
        url="https://other.com",
        method="GET",
        host="other.com",
        timestamp=0.0,
        headers={},
    )
    composite.on_request(other_request)

    assert calls == [
        ("global", "example.com"),
        ("host", "example.com"),
        ("global", "other.com"),
        ("other", "other.com"),
    ]


class _MetricStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def labels(self, **labels: str) -> "_MetricStub":
        self.calls.append(("labels", labels))
        return self

    def inc(self, amount: float = 1.0) -> None:
        self.calls.append(("inc", amount))

    def observe(self, amount: float) -> None:
        self.calls.append(("observe", amount))

    def set(self, value: float) -> None:
        self.calls.append(("set", value))


@pytest.fixture
def stubbed_metrics(monkeypatch: pytest.MonkeyPatch) -> dict[str, _MetricStub]:
    metrics = {
        "counter": _MetricStub(),
        "duration": _MetricStub(),
        "size": _MetricStub(),
        "backoff": _MetricStub(),
        "depth": _MetricStub(),
        "saturation": _MetricStub(),
        "retries": _MetricStub(),
    }
    monkeypatch.setattr("Medical_KG.ingestion.telemetry._REQUEST_COUNTER", metrics["counter"])
    monkeypatch.setattr(
        "Medical_KG.ingestion.telemetry._DURATION_HISTOGRAM", metrics["duration"]
    )
    monkeypatch.setattr(
        "Medical_KG.ingestion.telemetry._RESPONSE_SIZE_HISTOGRAM", metrics["size"]
    )
    monkeypatch.setattr(
        "Medical_KG.ingestion.telemetry._BACKOFF_HISTOGRAM", metrics["backoff"]
    )
    monkeypatch.setattr("Medical_KG.ingestion.telemetry._QUEUE_DEPTH_GAUGE", metrics["depth"])
    monkeypatch.setattr(
        "Medical_KG.ingestion.telemetry._QUEUE_SATURATION_GAUGE", metrics["saturation"]
    )
    monkeypatch.setattr("Medical_KG.ingestion.telemetry._RETRY_COUNTER", metrics["retries"])
    monkeypatch.setattr(
        PrometheusTelemetry,
        "is_available",
        staticmethod(lambda: True),
    )
    return metrics


def test_prometheus_telemetry_updates_metrics(stubbed_metrics: dict[str, _MetricStub]) -> None:
    telemetry = PrometheusTelemetry()
    request_id = generate_request_id()
    telemetry.on_response(
        HttpResponseEvent(
            request_id=request_id,
            url="https://example.com",
            method="GET",
            host="example.com",
            timestamp=1.0,
            status_code=200,
            duration_seconds=0.12,
            response_size_bytes=512,
            headers={},
        )
    )
    telemetry.on_backoff(
        HttpBackoffEvent(
            request_id=request_id,
            url="https://example.com",
            method="GET",
            host="example.com",
            timestamp=1.0,
            wait_time_seconds=0.05,
            queue_depth=2,
            queue_capacity=4,
            queue_saturation=0.5,
        )
    )
    telemetry.on_retry(
        HttpRetryEvent(
            request_id=request_id,
            url="https://example.com",
            method="GET",
            host="example.com",
            timestamp=1.0,
            attempt=1,
            delay_seconds=0.5,
            reason="timeout",
            will_retry=True,
        )
    )
    telemetry.on_error(
        HttpErrorEvent(
            request_id=request_id,
            url="https://example.com",
            method="GET",
            host="example.com",
            timestamp=1.5,
            error_type="HTTPError",
            message="boom",
            retryable=False,
        )
    )

    counter_calls = stubbed_metrics["counter"].calls
    assert counter_calls[0][0] == "labels"
    assert counter_calls[0][1]["status"] == "200"
    assert ("inc", 1.0) in counter_calls
    error_call = counter_calls[-2]
    assert error_call[1]["status"] == "HTTPError"

    depth_calls = stubbed_metrics["depth"].calls
    assert ("set", 2.0) in depth_calls
    saturation_calls = stubbed_metrics["saturation"].calls
    assert saturation_calls[-1] == ("set", 0.5)

    retry_calls = stubbed_metrics["retries"].calls
    assert retry_calls[-1][0] == "inc"


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.exceptions: list[tuple[Exception, dict[str, Any]]] = []
        self.ended: bool = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any], timestamp: int) -> None:
        self.events.append((name, attributes))

    def record_exception(
        self, exception: Exception, attributes: dict[str, Any], timestamp: int
    ) -> None:
        self.exceptions.append((exception, attributes))

    def end(self, end_time: int | None = None) -> None:
        self.ended = True


class _FakeTracer:
    def __init__(self) -> None:
        self.spans: list[_FakeSpan] = []

    def start_span(self, name: str, attributes: dict[str, Any], start_time: int) -> _FakeSpan:
        span = _FakeSpan()
        span.attributes.update(attributes)
        self.spans.append(span)
        return span


def test_tracing_telemetry_tracks_request_lifecycle() -> None:
    tracer = _FakeTracer()
    telemetry = TracingTelemetry(tracer=tracer)
    request_id = generate_request_id()
    request_event = HttpRequestEvent(
        request_id=request_id,
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.0,
        headers={},
    )
    telemetry.on_request(request_event)

    backoff_event = HttpBackoffEvent(
        request_id=request_id,
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.1,
        wait_time_seconds=0.05,
        queue_depth=1,
        queue_capacity=2,
        queue_saturation=0.5,
    )
    telemetry.on_backoff(backoff_event)

    retry_event = HttpRetryEvent(
        request_id=request_id,
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.2,
        attempt=1,
        delay_seconds=0.1,
        reason="timeout",
        will_retry=True,
    )
    telemetry.on_retry(retry_event)

    response_event = HttpResponseEvent(
        request_id=request_id,
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.3,
        status_code=200,
        duration_seconds=0.2,
        response_size_bytes=128,
        headers={},
    )
    telemetry.on_response(response_event)

    assert tracer.spans
    span = tracer.spans[0]
    assert span.attributes["http.method"] == "GET"
    assert any(name == "http.retry" for name, _ in span.events)
    assert span.ended is True

    telemetry.on_request(request_event)
    error_event = HttpErrorEvent(
        request_id=request_id,
        url="https://example.com",
        method="GET",
        host="example.com",
        timestamp=0.5,
        error_type="Timeout",
        message="boom",
        retryable=False,
    )
    telemetry.on_error(error_event)
    assert tracer.spans[-1].ended is True
