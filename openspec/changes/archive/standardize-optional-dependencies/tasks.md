# Implementation Tasks

## 1. Design MissingDependencyError

- [x] 1.1 Create `MissingDependencyError` exception class
- [x] 1.2 Add fields: feature_name, package_name, extras_group, install_hint
- [x] 1.3 Implement `__str__()` with clear, actionable message
- [x] 1.4 Add optional `docs_url` field for feature documentation
- [x] 1.5 Add comprehensive docstring with examples
- [x] 1.6 Add type hints for all fields

## 2. Create Dependency Registry

- [x] 2.1 Create `DEPENDENCY_REGISTRY` dict mapping features to packages
- [x] 2.2 Map observability → prometheus_client, opentelemetry
- [x] 2.3 Map pdf_processing → pypdf, pdfminer
- [x] 2.4 Map embeddings → sentence-transformers, faiss
- [x] 2.5 Map all optional dependencies with extras groups
- [x] 2.6 Document registry structure

## 3. Update Optional Import Helper

- [x] 3.1 Update `optional_import()` to raise `MissingDependencyError`
- [x] 3.2 Look up feature in registry for install hint
- [x] 3.3 Generate install command: `pip install medical-kg[feature]`
- [x] 3.4 Add fallback for unmapped packages
- [x] 3.5 Maintain backwards compatibility (same signature)
- [x] 3.6 Add comprehensive tests

## 4. Replace ModuleNotFoundError Usage

- [x] 4.1 Audit all `try/except ModuleNotFoundError` blocks
- [x] 4.2 Replace with `MissingDependencyError` where appropriate
- [x] 4.3 Update observability imports (`prometheus_client`, etc.)
- [x] 4.4 Update PDF processing imports
- [x] 4.5 Update embeddings imports
- [x] 4.6 Update all optional feature imports
- [x] 4.7 Test each replacement

## 5. Create Protocol Shims

- [x] 5.1 Create `stubs/prometheus_client.pyi` stub file
- [x] 5.2 Create `stubs/opentelemetry.pyi` stub file
- [x] 5.3 Define protocol classes for key interfaces
- [x] 5.4 Add minimal type hints for optional packages
- [x] 5.5 Test mypy accepts protocol shims
- [x] 5.6 Document stub maintenance process

## 6. Reduce mypy ignore_errors

- [x] 6.1 Audit current `ignore_errors` list in pyproject.toml
- [x] 6.2 Remove entries where protocol shims provide types
- [x] 6.3 Run mypy --strict incrementally
- [x] 6.4 Fix type errors revealed by removing ignores
- [x] 6.5 Track progress: measure % reduction
- [x] 6.6 Target 50%+ reduction in ignore list
- [x] 6.7 Document remaining necessary ignores

## 7. Document Dependency Matrix

- [x] 7.1 Create `docs/dependencies.md` guide
- [x] 7.2 List all extras groups with included packages
- [x] 7.3 Document which features require which extras
- [x] 7.4 Add installation examples for each extras group
- [x] 7.5 Document how to add new optional dependencies
- [x] 7.6 Add troubleshooting section
- [x] 7.7 Link from README and CONTRIBUTING

## 8. Update pyproject.toml

- [x] 8.1 Audit all `[project.optional-dependencies]` groups
- [x] 8.2 Ensure groups match DEPENDENCY_REGISTRY
- [x] 8.3 Add missing extras groups if needed
- [x] 8.4 Document each extras group with comments
- [x] 8.5 Test installation of each extras group
- [x] 8.6 Update CI matrix to test without optional deps

## 9. Add Import Error Tests

- [x] 9.1 Test MissingDependencyError raised when package missing
- [x] 9.2 Test install hint includes correct extras group
- [x] 9.3 Test all optional features raise helpful errors
- [x] 9.4 Test error message format is user-friendly
- [x] 9.5 Test docs_url included when available
- [x] 9.6 Mock missing imports in tests (don't require uninstall)

## 10. Add CLI Diagnostic Command

- [x] 10.1 Create `med dependencies check` command
- [x] 10.2 List all optional dependency groups
- [x] 10.3 Check which are installed vs missing
- [x] 10.4 Show install commands for missing groups
- [x] 10.5 Add `--verbose` flag for detailed info
- [x] 10.6 Add JSON output mode for scripting

## 11. Update CI Configuration

- [x] 11.1 Add CI job testing without optional dependencies
- [x] 11.2 Add CI job testing each extras group independently
- [x] 11.3 Test MissingDependencyError raised correctly in CI
- [x] 11.4 Add mypy check with reduced ignore list
- [x] 11.5 Monitor CI for import errors
- [x] 11.6 Document CI dependency testing strategy

## 12. Update Documentation

- [x] 12.1 Update README with extras installation examples
- [x] 12.2 Update CONTRIBUTING with dependency guidelines
- [x] 12.3 Document how to handle optional imports
- [x] 12.4 Add troubleshooting guide for import errors
- [x] 12.5 Document protocol shim maintenance
- [x] 12.6 Update operations manual

## 13. Migration and Communication

- [x] 13.1 Create migration guide for contributors
- [x] 13.2 Update all internal code to new pattern
- [x] 13.3 Communicate changes to external users
- [x] 13.4 Provide examples of before/after patterns
- [x] 13.5 Monitor for feedback and issues
- [x] 13.6 Adjust documentation based on feedback

## 14. Validation and Rollout

- [ ] 14.1 Run full test suite - all tests pass
- [ ] 14.2 Run mypy --strict with reduced ignores
- [ ] 14.3 Test with minimal dependencies (no extras)
- [ ] 14.4 Test with each extras group
- [x] 14.5 Verify error messages helpful for users
- [ ] 14.6 Deploy to staging
- [ ] 14.7 Production deployment
- [ ] 14.8 Monitor for import-related issues
