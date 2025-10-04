# Tasks: Normalize HTTP Client Telemetry

## 1. Audit Current Telemetry Implementation

- [ ] 1.1 Document all uses of `_NoopMetric` in http_client.py
- [ ] 1.2 Identify Prometheus auto-detection logic
- [ ] 1.3 Review `_TelemetryRegistry` implementation
- [ ] 1.4 Check adapter telemetry registration patterns
- [ ] 1.5 Grep for orphaned metric registration code
- [ ] 1.6 Document current metrics configuration approach

## 2. Remove _NoopMetric Placeholders

- [ ] 2.1 Delete `_NoopMetric` class definition
- [ ] 2.2 Delete `HTTP_REQUESTS = _NoopMetric()` global
- [ ] 2.3 Delete `HTTP_LATENCY = _NoopMetric()` global
- [ ] 2.4 Remove any other `_NoopMetric` instances
- [ ] 2.5 Clean up related imports
- [ ] 2.6 Verify no code depends on noop metrics
- [ ] 2.7 Run mypy strict on http_client.py

## 3. Centralize Telemetry Registration

- [ ] 3.1 Move all telemetry logic to `_TelemetryRegistry`
- [ ] 3.2 Ensure registry handles all event types
- [ ] 3.3 Remove duplicate registration code paths
- [ ] 3.4 Consolidate per-host callback handling
- [ ] 3.5 Test registry with multiple telemetry handlers
- [ ] 3.6 Document registry API
- [ ] 3.7 Add registry usage examples

## 4. Make Metrics Configuration Explicit

- [ ] 4.1 Change `enable_metrics` default to `False` (explicit opt-in)
- [ ] 4.2 Remove implicit Prometheus detection logic
- [ ] 4.3 Document how to enable Prometheus metrics
- [ ] 4.4 Add configuration examples to docstrings
- [ ] 4.5 Update default client initialization patterns
- [ ] 4.6 Test metrics enabled vs disabled paths
- [ ] 4.7 Document configuration best practices

## 5. Clean HTTP Client Constructor

- [ ] 5.1 Simplify telemetry parameter handling
- [ ] 5.2 Remove conditional Prometheus registration logic
- [ ] 5.3 Clean up callback initialization code
- [ ] 5.4 Update constructor docstring
- [ ] 5.5 Test constructor with various telemetry configs
- [ ] 5.6 Verify backwards compatibility where possible
- [ ] 5.7 Document breaking changes clearly

## 6. Update Adapter Instrumentation

- [ ] 6.1 Review adapter telemetry patterns in adapters/http.py
- [ ] 6.2 Ensure adapters use shared registry patterns
- [ ] 6.3 Remove any adapter-specific telemetry workarounds
- [ ] 6.4 Test adapter telemetry with normalized client
- [ ] 6.5 Update adapter documentation
- [ ] 6.6 Verify adapter telemetry overhead
- [ ] 6.7 Document adapter instrumentation patterns

## 7. Update Telemetry Helpers

- [ ] 7.1 Ensure `PrometheusTelemetry` integrates cleanly
- [ ] 7.2 Update `LoggingTelemetry` if needed
- [ ] 7.3 Test `CompositeTelemetry` with registry
- [ ] 7.4 Document helper usage patterns
- [ ] 7.5 Add examples for common scenarios
- [ ] 7.6 Test all helpers with normalized client
- [ ] 7.7 Update telemetry module documentation

## 8. Update Tests

- [ ] 8.1 Rewrite tests that depended on `_NoopMetric`
- [ ] 8.2 Update telemetry registration tests
- [ ] 8.3 Test explicit metrics configuration
- [ ] 8.4 Test telemetry enabled vs disabled
- [ ] 8.5 Add tests for normalized callback registration
- [ ] 8.6 Run full HTTP client test suite
- [ ] 8.7 Verify test coverage maintained

## 9. Update Configuration Documentation

- [ ] 9.1 Document explicit metrics enablement
- [ ] 9.2 Add configuration examples to runbook
- [ ] 9.3 Update adapter telemetry guide
- [ ] 9.4 Document Prometheus integration setup
- [ ] 9.5 Add troubleshooting for telemetry
- [ ] 9.6 Update API reference
- [ ] 9.7 Add migration guide for implicit→explicit config

## 10. Update Operations Guides

- [ ] 10.1 Update monitoring setup documentation
- [ ] 10.2 Document how to enable/disable metrics
- [ ] 10.3 Update Grafana dashboard setup instructions
- [ ] 10.4 Refresh telemetry troubleshooting guide
- [ ] 10.5 Document telemetry overhead expectations
- [ ] 10.6 Update capacity planning with telemetry costs
- [ ] 10.7 Add telemetry best practices

## 11. Performance Validation

- [ ] 11.1 Benchmark normalized telemetry overhead
- [ ] 11.2 Compare with previous implementation
- [ ] 11.3 Verify ≤2% overhead target met
- [ ] 11.4 Test with high request volumes
- [ ] 11.5 Profile telemetry hot paths
- [ ] 11.6 Document performance characteristics
- [ ] 11.7 Add performance regression tests

## 12. Migration Support

- [ ] 12.1 Identify code using implicit Prometheus detection
- [ ] 12.2 Update internal services to explicit config
- [ ] 12.3 Create migration guide for external users
- [ ] 12.4 Add deprecation notice if needed
- [ ] 12.5 Test migration path with real services
- [ ] 12.6 Document common migration issues
- [ ] 12.7 Provide migration assistance

## 13. Validation and Testing

- [ ] 13.1 Run full test suite - all tests pass
- [ ] 13.2 Run mypy --strict on telemetry modules
- [ ] 13.3 Verify no `_NoopMetric` references remain
- [ ] 13.4 Test metrics with Prometheus server
- [ ] 13.5 Verify telemetry overhead acceptable
- [ ] 13.6 Check for any regressions
- [ ] 13.7 Load test HTTP client with telemetry

## 14. Communication and Rollout

- [ ] 14.1 Announce telemetry normalization
- [ ] 14.2 Update release notes with config changes
- [ ] 14.3 Notify monitoring team
- [ ] 14.4 Create rollback procedure
- [ ] 14.5 Deploy to staging with monitoring
- [ ] 14.6 Verify staging telemetry working
- [ ] 14.7 Production deployment

## 15. Post-Deployment Monitoring

- [ ] 15.1 Monitor telemetry collection metrics
- [ ] 15.2 Verify Prometheus metrics flowing correctly
- [ ] 15.3 Check telemetry overhead in production
- [ ] 15.4 Monitor for telemetry-related errors
- [ ] 15.5 Verify dashboards showing data
- [ ] 15.6 Check for any performance impacts
- [ ] 15.7 Document completion and improvements
