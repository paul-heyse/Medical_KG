# Implementation Tasks

## 1. Design Event System

- [x] 1.1 Define `HttpEvent` base dataclass
- [x] 1.2 Define `HttpRequestEvent` (url, method, headers)
- [x] 1.3 Define `HttpResponseEvent` (status_code, duration, size)
- [x] 1.4 Define `HttpRetryEvent` (attempt, delay, reason)
- [x] 1.5 Define `HttpBackoffEvent` (wait_time, limiter_queue_depth)
- [x] 1.6 Define `HttpErrorEvent` (error_type, message, retryable)
- [x] 1.7 Add comprehensive docstrings

## 2. Implement Callback Interface

- [x] 2.1 Add `on_request` callback parameter to AsyncHttpClient
- [x] 2.2 Add `on_response` callback parameter
- [x] 2.3 Add `on_retry` callback parameter
- [x] 2.4 Add `on_backoff` callback parameter
- [x] 2.5 Add `on_error` callback parameter
- [x] 2.6 Make all callbacks optional (None by default)
- [x] 2.7 Document callback signatures

## 3. Emit Events in HTTP Lifecycle

- [x] 3.1 Emit `HttpRequestEvent` before making request
- [x] 3.2 Emit `HttpResponseEvent` after successful response
- [x] 3.3 Emit `HttpRetryEvent` when retrying request
- [x] 3.4 Emit `HttpBackoffEvent` when rate limited
- [x] 3.5 Emit `HttpErrorEvent` on exceptions
- [x] 3.6 Ensure events include full context
- [x] 3.7 Test event ordering is correct

## 4. Add Prometheus Metrics

- [x] 4.1 Add counter: `http_requests_total` by method, host, status
- [x] 4.2 Add histogram: `http_request_duration_seconds`
- [x] 4.3 Add histogram: `http_response_size_bytes`
- [x] 4.4 Add gauge: `http_limiter_queue_depth` by host
- [x] 4.5 Add histogram: `http_backoff_duration_seconds`
- [x] 4.6 Add counter: `http_retries_total` by reason
- [x] 4.7 Make metrics optional (only if prometheus installed)

## 5. Expose Limiter Queue Metrics

- [x] 5.1 Track current queue depth for each limiter
- [x] 5.2 Track queue wait time (time spent waiting for slot)
- [x] 5.3 Track queue saturation (% of time queue is full)
- [x] 5.4 Expose metrics via callbacks and Prometheus
- [x] 5.5 Add logging when queue exceeds threshold
- [x] 5.6 Document queue metrics in operations guide

## 6. Add Per-Host Instrumentation

- [x] 6.1 Track metrics separately by host
- [x] 6.2 Add host label to all Prometheus metrics
- [x] 6.3 Allow filtering callbacks by host
- [x] 6.4 Add per-host rate limit stats
- [x] 6.5 Document per-host monitoring patterns
- [x] 6.6 Test with multiple hosts

## 7. Create Telemetry Helpers

- [x] 7.1 Create `LoggingTelemetry` callback (structured logs)
- [x] 7.2 Create `PrometheusTelemetry` callback (metrics export)
- [x] 7.3 Create `TracingTelemetry` callback (OpenTelemetry spans)
- [x] 7.4 Create `CompositeTelemetry` (combine multiple callbacks)
- [x] 7.5 Document each helper with examples
- [x] 7.6 Add comprehensive tests

## 8. Update AsyncHttpClient Constructor

- [x] 8.1 Add `telemetry` parameter accepting callback or list
- [x] 8.2 Add `enable_metrics` parameter (bool, default True if prometheus available)
- [x] 8.3 Initialize callbacks during construction
- [x] 8.4 Maintain backwards compatibility (telemetry optional)
- [x] 8.5 Add comprehensive type hints
- [x] 8.6 Update docstring with telemetry examples

## 9. Add Adapter Integration

- [x] 9.1 Update `HttpAdapter` to accept telemetry callbacks
- [x] 9.2 Pass telemetry to AsyncHttpClient initialization
- [x] 9.3 Document adapter telemetry patterns
- [x] 9.4 Add examples for common telemetry scenarios
- [x] 9.5 Test adapter-specific telemetry
- [x] 9.6 Update adapter template

## 10. Add Comprehensive Tests

- [x] 10.1 Test events emitted for successful requests
- [x] 10.2 Test events emitted for failed requests
- [x] 10.3 Test retry events include attempt number
- [x] 10.4 Test backoff events include queue depth
- [x] 10.5 Test multiple callbacks work together
- [x] 10.6 Test per-host metrics isolation
- [x] 10.7 Test telemetry with real adapters
- [x] 10.8 Test performance (overhead < 5%)
- [x] 10.9 Test callback exceptions don't break requests
- [x] 10.10 Integration test with Prometheus exporter

## 11. Update Documentation

- [x] 11.1 Add "HTTP Client Telemetry" section to runbook
- [x] 11.2 Document all event types with examples
- [x] 11.3 Document callback interface
- [x] 11.4 Document built-in telemetry helpers
- [x] 11.5 Add monitoring guide (Prometheus dashboards)
- [x] 11.6 Document performance impact
- [x] 11.7 Add troubleshooting guide

## 12. Create Monitoring Dashboards

- [x] 12.1 Create Grafana dashboard for HTTP metrics
- [x] 12.2 Add panels for request rate by host
- [x] 12.3 Add panels for latency percentiles
- [x] 12.4 Add panels for error rate
- [x] 12.5 Add panels for retry counts
- [x] 12.6 Add panels for queue depth/saturation
- [x] 12.7 Export dashboard JSON to ops/monitoring/

## 13. Add Examples

- [x] 13.1 Example: Logging all requests to file
- [x] 13.2 Example: Tracking rate limit budget per host
- [x] 13.3 Example: Alerting on high retry rate
- [x] 13.4 Example: Custom telemetry for specific adapter
- [x] 13.5 Example: OpenTelemetry tracing integration
- [x] 13.6 Document examples in runbook

## 14. Validation and Rollout

- [ ] 14.1 Run full test suite - all tests pass
- [ ] 14.2 Run mypy --strict - no type errors
- [ ] 14.3 Benchmark performance overhead (target <5%)
- [ ] 14.4 Test with real adapters in staging
- [ ] 14.5 Monitor Prometheus metrics
- [ ] 14.6 Deploy to production with gradual rollout
- [ ] 14.7 Create alerts for HTTP health
- [ ] 14.8 Post-deployment monitoring (7 days)
