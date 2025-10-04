# HTTP Client Telemetry

## ADDED Requirements

### Requirement: HTTP Lifecycle Callbacks

The HTTP client SHALL provide callback hooks for observing HTTP request lifecycle events.

#### Scenario: Request event callback

- **WHEN** HTTP client begins a request
- **THEN** it SHALL invoke `on_request` callback if provided
- **AND** callback SHALL receive `HttpRequestEvent` with url, method, timestamp
- **AND** callback exception SHALL NOT break request execution

#### Scenario: Response event callback

- **WHEN** HTTP client receives a response
- **THEN** it SHALL invoke `on_response` callback if provided
- **AND** callback SHALL receive `HttpResponseEvent` with status, duration, size
- **AND** event SHALL include request context (url, method)

#### Scenario: Retry event callback

- **WHEN** HTTP client retries a request
- **THEN** it SHALL invoke `on_retry` callback if provided
- **AND** callback SHALL receive `HttpRetryEvent` with attempt number, delay, reason
- **AND** SHALL include whether retry will be attempted

#### Scenario: Backoff event callback

- **WHEN** HTTP client waits for rate limiter
- **THEN** it SHALL invoke `on_backoff` callback if provided
- **AND** callback SHALL receive `HttpBackoffEvent` with queue depth, wait time
- **AND** SHALL include queue saturation percentage

### Requirement: Prometheus Metrics Integration

The HTTP client SHALL provide built-in Prometheus metrics when `prometheus_client` is available.

#### Scenario: Request metrics

- **WHEN** Prometheus telemetry is enabled
- **THEN** client SHALL track `http_requests_total` counter by method, host, status
- **AND** SHALL track `http_request_duration_seconds` histogram by method, host
- **AND** SHALL track `http_response_size_bytes` histogram

#### Scenario: Rate limiter metrics

- **WHEN** rate limiting occurs
- **THEN** client SHALL expose `http_limiter_queue_depth` gauge by host
- **AND** SHALL track `http_backoff_duration_seconds` histogram
- **AND** metrics SHALL enable diagnosing saturation

#### Scenario: Retry metrics

- **WHEN** requests are retried
- **THEN** client SHALL track `http_retries_total` counter by reason
- **AND** SHALL enable identifying retry patterns

### Requirement: Per-Host Instrumentation

The HTTP client SHALL provide per-host metrics and filtering for targeted monitoring.

#### Scenario: Host-specific metrics

- **WHEN** metrics are exported
- **THEN** all metrics SHALL include `host` label
- **AND** SHALL enable per-API monitoring
- **AND** SHALL support host-specific alerts

#### Scenario: Callback filtering

- **WHEN** multiple hosts are accessed
- **THEN** callbacks CAN filter events by host
- **AND** adapters CAN register host-specific telemetry

### Requirement: Telemetry Helpers

The system SHALL provide built-in telemetry helpers for common use cases.

#### Scenario: Logging telemetry

- **WHEN** using `LoggingTelemetry` helper
- **THEN** HTTP events SHALL be logged with structured context
- **AND** SHALL support configurable log levels

#### Scenario: Composite telemetry

- **WHEN** using `CompositeTelemetry` helper
- **THEN** multiple callbacks CAN be combined
- **AND** SHALL invoke all callbacks in registration order
- **AND** one callback failure SHALL NOT affect others
