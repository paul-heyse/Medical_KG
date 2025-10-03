## Why

Security modules (license enforcement, retention policies, RBAC, audit logging, SHACL validation, provenance tracking) are minimally tested. Current `test_security.py` has basic coverage but misses critical scenarios: license tier filtering, retention policy execution, role-based access control, audit trail integrity, and SHACL constraint validation. Security bugs are high-impact and hard to detect in production.

## What Changes

- Add comprehensive tests for `licenses.py`: verify tier-based filtering, feature flags, and redaction logic across all license tiers (free, basic, pro, enterprise).
- Test `retention.py`: verify policy execution, data anonymization, audit log archival, and compliance with configurable retention periods.
- Test `rbac.py`: verify role assignment, permission checks, scope enforcement, and hierarchical role inheritance.
- Test `audit.py`: verify log entry creation, immutability, search/filter capabilities, and export functionality.
- Test `shacl.py`: verify SHACL shape validation against RDF graphs, constraint violation reporting, and custom rule loading.
- Test `provenance.py`: verify lineage tracking, entity attribution, and PROV-O serialization.
- Achieve 100% coverage for `src/Medical_KG/security/`.

## Impact

- Affected specs: `testing` (MODIFIED: Subsystem Test Depth to include security coverage requirements)
- Affected code: `tests/security/test_security.py` (expand), `src/Medical_KG/security/`, `tests/conftest.py` (new fixtures)
- Risks: security logic is often subtle; mitigation via property-based testing with `hypothesis` for license/RBAC edge cases.
