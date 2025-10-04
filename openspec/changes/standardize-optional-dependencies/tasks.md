# Implementation Tasks

## 1. Design MissingDependencyError

- [ ] 1.1 Create `MissingDependencyError` exception class
- [ ] 1.2 Add fields: feature_name, package_name, extras_group, install_hint
- [ ] 1.3 Implement `__str__()` with clear, actionable message
- [ ] 1.4 Add optional `docs_url` field for feature documentation
- [ ] 1.5 Add comprehensive docstring with examples
- [ ] 1.6 Add type hints for all fields

## 2. Create Dependency Registry

- [ ] 2.1 Create `DEPENDENCY_REGISTRY` dict mapping features to packages
- [ ] 2.2 Map observability → prometheus_client, opentelemetry
- [ ] 2.3 Map pdf_processing → pypdf, pdfminer
- [ ] 2.4 Map embeddings → sentence-transformers, faiss
- [ ] 2.5 Map all optional dependencies with extras groups
- [ ] 2.6 Document registry structure

## 3. Update Optional Import Helper

- [ ] 3.1 Update `optional_import()` to raise `MissingDependencyError`
- [ ] 3.2 Look up feature in registry for install hint
- [ ] 3.3 Generate install command: `pip install medical-kg[feature]`
- [ ] 3.4 Add fallback for unmapped packages
- [ ] 3.5 Maintain backwards compatibility (same signature)
- [ ] 3.6 Add comprehensive tests

## 4. Replace ModuleNotFoundError Usage

- [ ] 4.1 Audit all `try/except ModuleNotFoundError` blocks
- [ ] 4.2 Replace with `MissingDependencyError` where appropriate
- [ ] 4.3 Update observability imports (`prometheus_client`, etc.)
- [ ] 4.4 Update PDF processing imports
- [ ] 4.5 Update embeddings imports
- [ ] 4.6 Update all optional feature imports
- [ ] 4.7 Test each replacement

## 5. Create Protocol Shims

- [ ] 5.1 Create `stubs/prometheus_client.pyi` stub file
- [ ] 5.2 Create `stubs/opentelemetry.pyi` stub file
- [ ] 5.3 Define protocol classes for key interfaces
- [ ] 5.4 Add minimal type hints for optional packages
- [ ] 5.5 Test mypy accepts protocol shims
- [ ] 5.6 Document stub maintenance process

## 6. Reduce mypy ignore_errors

- [ ] 6.1 Audit current `ignore_errors` list in pyproject.toml
- [ ] 6.2 Remove entries where protocol shims provide types
- [ ] 6.3 Run mypy --strict incrementally
- [ ] 6.4 Fix type errors revealed by removing ignores
- [ ] 6.5 Track progress: measure % reduction
- [ ] 6.6 Target 50%+ reduction in ignore list
- [ ] 6.7 Document remaining necessary ignores

## 7. Document Dependency Matrix

- [ ] 7.1 Create `docs/dependencies.md` guide
- [ ] 7.2 List all extras groups with included packages
- [ ] 7.3 Document which features require which extras
- [ ] 7.4 Add installation examples for each extras group
- [ ] 7.5 Document how to add new optional dependencies
- [ ] 7.6 Add troubleshooting section
- [ ] 7.7 Link from README and CONTRIBUTING

## 8. Update pyproject.toml

- [ ] 8.1 Audit all `[project.optional-dependencies]` groups
- [ ] 8.2 Ensure groups match DEPENDENCY_REGISTRY
- [ ] 8.3 Add missing extras groups if needed
- [ ] 8.4 Document each extras group with comments
- [ ] 8.5 Test installation of each extras group
- [ ] 8.6 Update CI matrix to test without optional deps

## 9. Add Import Error Tests

- [ ] 9.1 Test MissingDependencyError raised when package missing
- [ ] 9.2 Test install hint includes correct extras group
- [ ] 9.3 Test all optional features raise helpful errors
- [ ] 9.4 Test error message format is user-friendly
- [ ] 9.5 Test docs_url included when available
- [ ] 9.6 Mock missing imports in tests (don't require uninstall)

## 10. Add CLI Diagnostic Command

- [ ] 10.1 Create `med dependencies check` command
- [ ] 10.2 List all optional dependency groups
- [ ] 10.3 Check which are installed vs missing
- [ ] 10.4 Show install commands for missing groups
- [ ] 10.5 Add `--verbose` flag for detailed info
- [ ] 10.6 Add JSON output mode for scripting

## 11. Update CI Configuration

- [ ] 11.1 Add CI job testing without optional dependencies
- [ ] 11.2 Add CI job testing each extras group independently
- [ ] 11.3 Test MissingDependencyError raised correctly in CI
- [ ] 11.4 Add mypy check with reduced ignore list
- [ ] 11.5 Monitor CI for import errors
- [ ] 11.6 Document CI dependency testing strategy

## 12. Update Documentation

- [ ] 12.1 Update README with extras installation examples
- [ ] 12.2 Update CONTRIBUTING with dependency guidelines
- [ ] 12.3 Document how to handle optional imports
- [ ] 12.4 Add troubleshooting guide for import errors
- [ ] 12.5 Document protocol shim maintenance
- [ ] 12.6 Update operations manual

## 13. Migration and Communication

- [ ] 13.1 Create migration guide for contributors
- [ ] 13.2 Update all internal code to new pattern
- [ ] 13.3 Communicate changes to external users
- [ ] 13.4 Provide examples of before/after patterns
- [ ] 13.5 Monitor for feedback and issues
- [ ] 13.6 Adjust documentation based on feedback

## 14. Validation and Rollout

- [ ] 14.1 Run full test suite - all tests pass
- [ ] 14.2 Run mypy --strict with reduced ignores
- [ ] 14.3 Test with minimal dependencies (no extras)
- [ ] 14.4 Test with each extras group
- [ ] 14.5 Verify error messages helpful for users
- [ ] 14.6 Deploy to staging
- [ ] 14.7 Production deployment
- [ ] 14.8 Monitor for import-related issues
