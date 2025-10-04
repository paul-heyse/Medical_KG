# Implementation Tasks

## 1. Design Event System

- [ ] 1.1 Define `HttpEvent` base dataclass
- [ ] 1.2 Define `HttpRequestEvent` (url, method, headers)
- [ ] 1.3 Define `HttpResponseEvent` (status_code, duration, size)
- [ ] 1.4 Define `HttpRetryEvent` (attempt, delay, reason)
- [ ] 1.5 Define `HttpBackoffEvent` (wait_time, limiter_queue_depth)
- [ ] 1.6 Define `HttpErrorEvent` (error_type, message, retryable)
- [ ] 1.7 Add comprehensive docstrings

## 2. Implement Callback Interface

- [ ] 2.1 Add `on_request` callback parameter to AsyncHttpClient
- [ ] 2.2 Add `on_response` callback parameter
- [ ] 2.3 Add `on_retry` callback parameter
- [ ] 2.4 Add `on_backoff` callback parameter
- [ ] 2.5 Add `on_error` callback parameter
- [ ] 2.6 Make all callbacks optional (None by default)
- [ ] 2.7 Document callback signatures

## 3. Emit Events in HTTP Lifecycle

- [ ] 3.1 Emit `HttpRequestEvent` before making request
- [ ] 3.2 Emit `HttpResponseEvent` after successful response
- [ ] 3.3 Emit `HttpRetryEvent` when retrying request
- [ ] 3.4 Emit `HttpBackoffEvent` when rate limited
- [ ] 3.5 Emit `HttpErrorEvent` on exceptions
- [ ] 3.6 Ensure events include full context
- [ ] 3.7 Test event ordering is correct

## 4. Add Prometheus Metrics

- [ ] 4.1 Add counter: `http_requests_total` by method, host, status
- [ ] 4.2 Add histogram: `http_request_duration_seconds`
- [ ] 4.3 Add histogram: `http_response_size_bytes`
- [ ] 4.4 Add gauge: `http_limiter_queue_depth` by host
- [ ] 4.5 Add histogram: `http_backoff_duration_seconds`
- [ ] 4.6 Add counter: `http_retries_total` by reason
- [ ] 4.7 Make metrics optional (only if prometheus installed)

## 5. Expose Limiter Queue Metrics

- [ ] 5.1 Track current queue depth for each limiter
- [ ] 5.2 Track queue wait time (time spent waiting for slot)
- [ ] 5.3 Track queue saturation (% of time queue is full)
- [ ] 5.4 Expose metrics via callbacks and Prometheus
- [ ] 5.5 Add logging when queue exceeds threshold
- [ ] 5.6 Document queue metrics in operations guide

## 6. Add Per-Host Instrumentation

- [ ] 6.1 Track metrics separately by host
- [ ] 6.2 Add host label to all Prometheus metrics
- [ ] 6.3 Allow filtering callbacks by host
- [ ] 6.4 Add per-host rate limit stats
- [ ] 6.5 Document per-host monitoring patterns
- [ ] 6.6 Test with multiple hosts

## 7. Create Telemetry Helpers

- [ ] 7.1 Create `LoggingTelemetry` callback (structured logs)
- [ ] 7.2 Create `PrometheusTelemetry` callback (metrics export)
- [ ] 7.3 Create `TracingTelemetry` callback (OpenTelemetry spans)
- [ ] 7.4 Create `CompositeTelemetry` (combine multiple callbacks)
- [ ] 7.5 Document each helper with examples
- [ ] 7.6 Add comprehensive tests

## 8. Update AsyncHttpClient Constructor

- [ ] 8.1 Add `telemetry` parameter accepting callback or list
- [ ] 8.2 Add `enable_metrics` parameter (bool, default True if prometheus available)
- [ ] 8.3 Initialize callbacks during construction
- [ ] 8.4 Maintain backwards compatibility (telemetry optional)
- [ ] 8.5 Add comprehensive type hints
- [ ] 8.6 Update docstring with telemetry examples

## 9. Add Adapter Integration

- [ ] 9.1 Update `HttpAdapter` to accept telemetry callbacks
- [ ] 9.2 Pass telemetry to AsyncHttpClient initialization
- [ ] 9.3 Document adapter telemetry patterns
- [ ] 9.4 Add examples for common telemetry scenarios
- [ ] 9.5 Test adapter-specific telemetry
- [ ] 9.6 Update adapter template

## 10. Add Comprehensive Tests

- [ ] 10.1 Test events emitted for successful requests
- [ ] 10.2 Test events emitted for failed requests
- [ ] 10.3 Test retry events include attempt number
- [ ] 10.4 Test backoff events include queue depth
- [ ] 10.5 Test multiple callbacks work together
- [ ] 10.6 Test per-host metrics isolation
- [ ] 10.7 Test telemetry with real adapters
- [ ] 10.8 Test performance (overhead < 5%)
- [ ] 10.9 Test callback exceptions don't break requests
- [ ] 10.10 Integration test with Prometheus exporter

## 11. Update Documentation

- [ ] 11.1 Add "HTTP Client Telemetry" section to runbook
- [ ] 11.2 Document all event types with examples
- [ ] 11.3 Document callback interface
- [ ] 11.4 Document built-in telemetry helpers
- [ ] 11.5 Add monitoring guide (Prometheus dashboards)
- [ ] 11.6 Document performance impact
- [ ] 11.7 Add troubleshooting guide

## 12. Create Monitoring Dashboards

- [ ] 12.1 Create Grafana dashboard for HTTP metrics
- [ ] 12.2 Add panels for request rate by host
- [ ] 12.3 Add panels for latency percentiles
- [ ] 12.4 Add panels for error rate
- [ ] 12.5 Add panels for retry counts
- [ ] 12.6 Add panels for queue depth/saturation
- [ ] 12.7 Export dashboard JSON to ops/monitoring/

## 13. Add Examples

- [ ] 13.1 Example: Logging all requests to file
- [ ] 13.2 Example: Tracking rate limit budget per host
- [ ] 13.3 Example: Alerting on high retry rate
- [ ] 13.4 Example: Custom telemetry for specific adapter
- [ ] 13.5 Example: OpenTelemetry tracing integration
- [ ] 13.6 Document examples in runbook

## 14. Validation and Rollout

- [ ] 14.1 Run full test suite - all tests pass
- [ ] 14.2 Run mypy --strict - no type errors
- [ ] 14.3 Benchmark performance overhead (target <5%)
- [ ] 14.4 Test with real adapters in staging
- [ ] 14.5 Monitor Prometheus metrics
- [ ] 14.6 Deploy to production with gradual rollout
- [ ] 14.7 Create alerts for HTTP health
- [ ] 14.8 Post-deployment monitoring (7 days)
