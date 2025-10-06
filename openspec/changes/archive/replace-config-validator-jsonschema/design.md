# Config Validator Replacement Design

## Context

`ConfigValidator` in `config/manager.py` reimplements ~200 lines of JSON Schema functionality:

- Custom ref resolution
- Manual enum/range checking
- Bespoke error messages
- Must update whenever schemas evolve

The `jsonschema` library is already a project dependency (used in CLI validation) and provides:

- Full JSON Schema Draft 7 support
- Better error messages with JSON pointers
- Format validators (email, uri, date-time)
- Advanced features (oneOf, anyOf, if/then/else)
- Well-tested, maintained by community

## Goals

- Replace custom validator with `jsonschema`
- Reduce custom validation code by ~200 lines
- Improve error message clarity
- Support advanced schema features
- Add schema versioning

## Non-Goals

- Not changing config file format (still YAML/JSON)
- Not rewriting existing schemas (minor updates only)
- Not adding new validation rules (feature parity first)

## Decisions

### Decision 1: JSON Schema Draft 7

**Choice**: Use Draft 7 (widely supported, stable)

**Rationale**: Draft 7 has best tooling support, stable spec, sufficient features

### Decision 2: Error Message Enhancement

**Choice**: Parse `ValidationError` and add context

```python
def format_validation_error(error: ValidationError, config_file: str) -> str:
    pointer = "/".join(str(p) for p in error.absolute_path)
    return f"""
Configuration error in {config_file}:
  Location: {pointer}
  Problem: {error.message}
  Value: {error.instance}
  Hint: {get_remediation_hint(error)}
"""
```

### Decision 3: Custom Format Validators

**Choice**: Register domain-specific validators

```python
def validate_duration(value: str) -> bool:
    """Validate duration like '5m', '1h', '2d'."""
    return DURATION_PATTERN.match(value) is not None

jsonschema.FormatChecker().checks("duration")(validate_duration)
```

### Decision 4: Schema Versioning

**Choice**: Add `version` field, validate compatibility

```python
# In schema
{"$schema": "http://json-schema.org/draft-07/schema#",
 "version": "1.2",
 "type": "object",
 ...}

# In validator
if schema_version < min_supported_version:
    raise IncompatibleSchemaVersion()
```

## Risks / Trade-offs

**Risk**: `jsonschema` dependency issues
**Mitigation**: Pin version, comprehensive tests

**Trade-off**: Slightly more verbose schemas
**Benefit**: Standard compliance, better tooling

## Migration Plan

1. Add `jsonschema` integration (keep custom validator)
2. Validate both match on staging
3. Switch to `jsonschema` in production
4. Remove custom validator after 30 days

## Success Criteria

- [ ] ~200 lines of custom code removed
- [ ] All configs validate with `jsonschema`
- [ ] Error messages clearer than before
- [ ] Schema version tracking works
