# Tasks: Normalize HTTP Client Telemetry

## 1. Audit Current Telemetry Implementation

- [x] 1.1 Document all uses of `_NoopMetric` in http_client.py *(removed placeholders; see updated docstrings and tests)*
- [x] 1.2 Identify Prometheus auto-detection logic *(replaced with explicit opt-in flag)*
- [x] 1.3 Review `_TelemetryRegistry` implementation *(extended with public registration helper)*
- [x] 1.4 Check adapter telemetry registration patterns *(base adapter now forwards telemetry to the shared client)*
- [x] 1.5 Grep for orphaned metric registration code *(cleaned direct metric mutations in `_execute`)*
- [x] 1.6 Document current metrics configuration approach *(runbook now covers explicit enablement)*

## 2. Remove _NoopMetric Placeholders

- [x] 2.1 Delete `_NoopMetric` class definition
- [x] 2.2 Delete `HTTP_REQUESTS = _NoopMetric()` global
- [x] 2.3 Delete `HTTP_LATENCY = _NoopMetric()` global
- [x] 2.4 Remove any other `_NoopMetric` instances
- [x] 2.5 Clean up related imports
- [x] 2.6 Verify no code depends on noop metrics *(tests cover telemetry fan-out)*
- [x] 2.7 Run mypy strict on http_client.py *(command executed; baseline API typing errors remain unrelated to this change)*

## 3. Centralize Telemetry Registration

- [x] 3.1 Move all telemetry logic to `_TelemetryRegistry`
- [x] 3.2 Ensure registry handles all event types *(registry now backs public add_telemetry API)*
- [x] 3.3 Remove duplicate registration code paths
- [x] 3.4 Consolidate per-host callback handling *(new host override path)*
- [x] 3.5 Test registry with multiple telemetry handlers *(expanded unit coverage)*
- [x] 3.6 Document registry API *(new docstrings and runbook guidance)*
- [x] 3.7 Add registry usage examples *(runbook snippet shows add_telemetry)*

## 4. Make Metrics Configuration Explicit

- [x] 4.1 Change `enable_metrics` default to `False` (explicit opt-in)
- [x] 4.2 Remove implicit Prometheus detection logic
- [x] 4.3 Document how to enable Prometheus metrics *(runbook + __init__ docstring)*
- [x] 4.4 Add configuration examples to docstrings
- [x] 4.5 Update default client initialization patterns *(tests + documentation use explicit opt-in)*
- [x] 4.6 Test metrics enabled vs disabled paths *(new Prometheus opt-in test exercises enabled; existing suite covers disabled default)*
- [x] 4.7 Document configuration best practices *(troubleshooting section updated)

## 5. Clean HTTP Client Constructor

- [x] 5.1 Simplify telemetry parameter handling *(single add_telemetry entry point)*
- [x] 5.2 Remove conditional Prometheus registration logic
- [x] 5.3 Clean up callback initialization code *(callbacks flow through registry)*
- [x] 5.4 Update constructor docstring
- [x] 5.5 Test constructor with various telemetry configs *(coverage for lists, mappings, and host overrides)*
- [x] 5.6 Verify backwards compatibility where possible *(adapter + pipeline tests ensure behaviour parity)*
- [x] 5.7 Document breaking changes clearly *(runbook highlights new opt-in default)

## 6. Update Adapter Instrumentation

- [x] 6.1 Review adapter telemetry patterns in adapters/http.py
- [x] 6.2 Ensure adapters use shared registry patterns *(base adapter forwards telemetry to client)*
- [x] 6.3 Remove any adapter-specific telemetry workarounds
- [x] 6.4 Test adapter telemetry with normalized client *(adapter test captures forwarded telemetry)*
- [x] 6.5 Update adapter documentation *(runbook notes HttpAdapter forwarding)*
- [ ] 6.6 Verify adapter telemetry overhead
- [x] 6.7 Document adapter instrumentation patterns

## 7. Update Telemetry Helpers

- [x] 7.1 Ensure `PrometheusTelemetry` integrates cleanly *(opt-in test validates event flow)*
- [ ] 7.2 Update `LoggingTelemetry` if needed
- [ ] 7.3 Test `CompositeTelemetry` with registry
- [x] 7.4 Document helper usage patterns *(runbook now explains add_telemetry and Prometheus opt-in)*
- [x] 7.5 Add examples for common scenarios *(documentation includes explicit enablement + per-host snippets)*
- [ ] 7.6 Test all helpers with normalized client
- [ ] 7.7 Update telemetry module documentation

## 8. Update Tests

- [x] 8.1 Rewrite tests that depended on `_NoopMetric`
- [x] 8.2 Update telemetry registration tests
- [x] 8.3 Test explicit metrics configuration
- [x] 8.4 Test telemetry enabled vs disabled *(default path exercised by suite; opt-in covered explicitly)*
- [x] 8.5 Add tests for normalized callback registration
- [x] 8.6 Run full HTTP client test suite
- [ ] 8.7 Verify test coverage maintained

## 9. Update Configuration Documentation

- [x] 9.1 Document explicit metrics enablement *(Prometheus section now calls out opt-in flow)*
- [x] 9.2 Add configuration examples to runbook *(added code snippets for enabling metrics)*
- [x] 9.3 Update adapter telemetry guide *(clarified HttpAdapter forwarding semantics)*
- [x] 9.4 Document Prometheus integration setup *(runbook explains dependency + opt-in requirements)*
- [x] 9.5 Add troubleshooting for telemetry *(updated guidance for missing metrics scenarios)*
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
