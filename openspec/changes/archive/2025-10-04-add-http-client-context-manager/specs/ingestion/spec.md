# HTTP Client Context Manager Support

## ADDED Requirements

### Requirement: AsyncHttpClient Context Manager Protocol

The HTTP client SHALL support the async context manager protocol to enable automatic resource cleanup and prevent resource leaks.

#### Scenario: Basic context manager usage

- **WHEN** a developer creates an AsyncHttpClient using `async with` statement
- **THEN** the client SHALL be properly initialized in `__aenter__`
- **AND** SHALL automatically call `aclose()` in `__aexit__` after the block
- **AND** SHALL release all network resources

#### Scenario: Cleanup on exception

- **WHEN** an exception occurs within the `async with` block
- **THEN** the client SHALL still call `aclose()` in `__aexit__`
- **AND** SHALL properly propagate the exception
- **AND** SHALL NOT leak network resources

#### Scenario: Nested context managers

- **WHEN** multiple AsyncHttpClient instances are used in nested contexts
- **THEN** each client SHALL manage its own resources independently
- **AND** cleanup SHALL happen in correct order (inner to outer)
- **AND** exception in one SHALL NOT prevent cleanup of others

#### Scenario: Backward compatibility

- **WHEN** existing code uses manual `aclose()` calls
- **THEN** the client SHALL continue to support manual lifecycle management
- **AND** SHALL NOT require refactoring to context managers
- **AND** SHALL allow mixing of both patterns in same codebase

