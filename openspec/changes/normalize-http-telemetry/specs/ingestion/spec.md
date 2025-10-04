# Spec Delta: HTTP Client Telemetry (normalize-http-telemetry)

## REMOVED Requirements

### Requirement: NoopMetric Placeholder System

**Reason**: Structured telemetry hooks eliminate need for placeholders

**Migration**: Use `enable_metrics=True` to enable Prometheus metrics or provide custom telemetry callbacks

Noop metrics were used when Prometheus was unavailable, providing no-op implementations of metric methods.

### Requirement: Implicit Prometheus Detection

**Reason**: Explicit configuration is more predictable

**Migration**: Set `enable_metrics=True` explicitly to enable Prometheus integration

Auto-detection imported `prometheus_client` during initialization to determine if metrics should be enabled.

## MODIFIED Requirements

### Requirement: HTTP Client Telemetry Integration

The HTTP client SHALL provide structured telemetry via explicit callback registration without placeholder metrics.

**Modifications**:

- Removed `_NoopMetric` placeholder classes
- Made Prometheus metrics opt-in via `enable_metrics` parameter
- Centralized all telemetry through `_TelemetryRegistry`

#### Scenario: Enable Prometheus metrics explicitly

- **GIVEN** `AsyncHttpClient` initialization
- **WHEN** `enable_metrics=True` is specified
- **THEN** `PrometheusTelemetry` is registered automatically
- **AND** HTTP lifecycle events emit Prometheus metrics
- **AND** no noop placeholders are used

#### Scenario: Disable metrics by default

- **GIVEN** `AsyncHttpClient` initialization without `enable_metrics`
- **WHEN** the client is constructed
- **THEN** metrics are disabled by default
- **AND** no Prometheus dependencies are required
- **AND** telemetry overhead is minimal

#### Scenario: Custom telemetry registration

- **GIVEN** a custom `HttpTelemetry` implementation
- **WHEN** passed to `telemetry` parameter
- **THEN** callbacks are registered via `_TelemetryRegistry`
- **AND** events are emitted to custom handler
- **AND** no implicit Prometheus metrics are added

### Requirement: Telemetry Registry

The HTTP client SHALL manage telemetry callbacks through a centralized registry.

**Modifications**:

- Consolidated all telemetry registration through `_TelemetryRegistry`
- Removed duplicate registration logic
- Simplified per-host callback handling

#### Scenario: Register telemetry callbacks

- **GIVEN** multiple telemetry handlers
- **WHEN** registered with the HTTP client
- **THEN** `_TelemetryRegistry` manages all callbacks
- **AND** events are dispatched to all registered handlers
- **AND** exceptions in handlers don't break requests

#### Scenario: Per-host telemetry

- **GIVEN** host-specific telemetry configuration
- **WHEN** requests are made to different hosts
- **THEN** appropriate host-specific handlers receive events
- **AND** global handlers receive all events
- **AND** telemetry is correctly scoped by host

### Requirement: Telemetry Configuration

The HTTP client SHALL provide explicit configuration for metrics and telemetry.

**Modifications**:

- Changed `enable_metrics` to explicit opt-in (default `False`)
- Removed implicit feature detection
- Added clear documentation for configuration options

#### Scenario: Configure Prometheus metrics

- **GIVEN** a service wanting Prometheus metrics
- **WHEN** `AsyncHttpClient(enable_metrics=True)` is used
- **THEN** Prometheus telemetry is enabled
- **AND** configuration is explicit and documented
- **AND** no auto-detection occurs

#### Scenario: Telemetry overhead

- **GIVEN** an HTTP client with telemetry enabled
- **WHEN** making HTTP requests
- **THEN** telemetry overhead is ≤2%
- **AND** performance is predictable
- **AND** overhead is documented
