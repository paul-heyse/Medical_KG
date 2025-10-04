# HTTP Client Telemetry Design

## Context

`AsyncHttpClient` handles retries and rate limiting but provides no visibility into:

- Retry attempts and reasons
- Rate limit queue saturation
- Per-host performance
- Backpressure events

Teams building custom telemetry duplicate logic around the client instead of using structured hooks.

## Goals

- Add observable hooks for HTTP lifecycle
- Expose limiter queue metrics
- Enable per-host instrumentation
- Keep hooks optional (zero overhead if unused)
- Provide built-in Prometheus integration

## Non-Goals

- Not changing HTTP client interface (additive only)
- Not adding distributed tracing (adapters can add via callbacks)
- Not requiring telemetry dependencies

## Decisions

### Decision 1: Callback-Based Events

**Choice**: Callbacks passed to constructor, invoked at lifecycle points

```python
@dataclass
class HttpRequestEvent:
    url: str
    method: str
    timestamp: float
    headers: dict[str, str]  # Sanitized

client = AsyncHttpClient(
    on_request=lambda event: logger.info(f"HTTP {event.method} {event.url}"),
    on_response=lambda event: metrics.track_latency(event.duration),
    on_retry=lambda event: metrics.increment("retries", {"attempt": event.attempt}),
    on_backoff=lambda event: metrics.gauge("queue_depth", event.queue_depth),
)
```

**Rationale**:

- Simple: Standard Python callback pattern
- Flexible: Can compose multiple callbacks
- Zero overhead: No-op if callbacks None
- Type-safe: Mypy validates callback signatures

**Alternatives considered**:

- **Event emitter**: More complex, similar functionality
- **Subclassing**: Less composable, harder to test
- **Middleware**: Over-engineered for this use case

### Decision 2: Built-in Prometheus Integration

**Choice**: Provide `PrometheusTelemetry` helper that wires callbacks to metrics

```python
from Medical_KG.observability.telemetry import PrometheusTelemetry

telemetry = PrometheusTelemetry()
client = AsyncHttpClient(
    on_request=telemetry.on_request,
    on_response=telemetry.on_response,
    on_retry=telemetry.on_retry,
)
# Metrics automatically exported to Prometheus
```

**Metrics**:

- `http_requests_total{method, host, status}`
- `http_request_duration_seconds{method, host}`
- `http_limiter_queue_depth{host}`
- `http_retries_total{reason}`

**Rationale**:

- Most common use case
- Reduces boilerplate
- Optional (only if prometheus_client installed)
- Demonstrates pattern for custom telemetry

### Decision 3: Per-Host Metrics

**Choice**: Add `host` label to all metrics

**Rationale**:

- Identify problematic hosts
- Track per-API rate limits independently
- Diagnose saturation by API
- Enable host-specific alerts

### Decision 4: Limiter Queue Exposure

**Choice**: Track and expose queue depth/saturation in `HttpBackoffEvent`

```python
@dataclass
class HttpBackoffEvent:
    wait_time_seconds: float
    queue_depth: int
    queue_capacity: int
    queue_saturation: float  # depth / capacity
    host: str
```

**Rationale**:

- Diagnose rate limit issues
- Identify when to scale parallelism
- Observable backpressure
- Actionable for operators

## Risks / Trade-offs

**Risk**: Performance overhead from callbacks
**Mitigation**: Benchmark (<5% acceptable), make optional

**Risk**: Callback exceptions break requests
**Mitigation**: Wrap callbacks in try/except, log errors

**Trade-off**: More complexity in AsyncHttpClient
**Benefit**: Eliminates custom telemetry wrappers

## Migration Plan

1. Add callback interface (backwards compatible)
2. Deploy with telemetry disabled
3. Gradually enable for adapters
4. Monitor performance
5. Enable by default

## Success Criteria

- [ ] Callbacks invoked at correct lifecycle points
- [ ] Prometheus metrics exported correctly
- [ ] Per-host metrics isolated
- [ ] Performance overhead <5%
- [ ] Documentation with examples
