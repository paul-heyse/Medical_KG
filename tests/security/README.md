# Security Test Suite

This suite exercises license enforcement, RBAC, retention policies, audit logging, SHACL validation, and provenance tracking.

## Structure

- `test_license_registry.py` – unit tests for tiered licensing, usage limits, overrides, and expiration handling.
- `test_retention.py` – integration-style coverage for retention policies and audit logging side effects.
- `test_rbac.py` – RBAC role hierarchy and scope enforcement checks.
- `test_audit_logger.py` – append-only logging, search, export, rotation, and integrity verification.
- `test_shacl_validation.py` – graph constraint evaluation and dynamic shape composition.
- `test_provenance.py` – provenance lineage tracking, PROV-O serialization, and graph export.
- `test_property_based.py` – Hypothesis-powered regression tests for licenses, role inheritance, and retention safety.

## Running

```bash
pytest tests/security -q
```

The coverage hook in `tests/conftest.py` enforces ≥95% statement coverage. Exported coverage gaps are written to `coverage_missing.txt`.
