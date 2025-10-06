# Implementation Tasks

## 1. Audit Current Config Validator

- [x] 1.1 Document all features of custom `ConfigValidator` class
- [x] 1.2 List all validation rules (refs, enums, ranges, types)
- [x] 1.3 Identify `jsonschema` equivalents for each rule
- [x] 1.4 Find any custom validations that need preservation
- [x] 1.5 Document current error message format
- [x] 1.6 List all config files currently validated

## 2. Select jsonschema Version and Features

- [x] 2.1 Choose JSON Schema draft version (recommend Draft 7)
- [x] 2.2 Verify `jsonschema` library supports required features
- [x] 2.3 Document schema dialect to use (`$schema` field)
- [x] 2.4 Test `jsonschema` with existing config schemas
- [x] 2.5 Identify any feature gaps vs custom validator
- [x] 2.6 Plan workarounds for unsupported features

## 3. Update Config Schemas

- [x] 3.1 Add `$schema` field to all config files
- [x] 3.2 Convert custom validation annotations to standard keywords
- [x] 3.3 Test schema files validate with online validators
- [x] 3.4 Add schema version tracking (e.g., "version": "1.0")
- [x] 3.5 Document schema upgrade process
- [x] 3.6 Create schema changelog

## 4. Implement jsonschema Integration

- [x] 4.1 Add `jsonschema` to requirements.txt (if not present)
- [x] 4.2 Create `ConfigSchemaValidator` wrapper class
- [x] 4.3 Implement `validate(config: dict, schema: dict)` method
- [x] 4.4 Cache compiled schemas for performance
- [x] 4.5 Add format validators (email, uri, etc.)
- [x] 4.6 Add custom validators for domain-specific rules
- [x] 4.7 Ensure thread-safe schema cache

## 5. Improve Error Messages

- [x] 5.1 Parse `ValidationError` from jsonschema
- [x] 5.2 Extract JSON pointer to error location
- [x] 5.3 Format error with clear context (file, path, value)
- [x] 5.4 Add remediation hints for common errors
- [x] 5.5 Support multiple errors (collect all, not just first)
- [x] 5.6 Add color formatting for terminal output
- [x] 5.7 Test error messages with sample invalid configs

## 6. Remove Custom Validator

- [x] 6.1 Delete `ConfigValidator` class from config/manager.py
- [x] 6.2 Remove custom validation helper functions
- [x] 6.3 Remove manual ref resolution code
- [x] 6.4 Remove custom enum validation code
- [x] 6.5 Remove custom range validation code
- [x] 6.6 Clean up unused imports
- [x] 6.7 Verify ~200 lines removed

## 7. Update ConfigManager

- [x] 7.1 Replace `ConfigValidator` usage with `jsonschema`
- [x] 7.2 Update `load_config()` to use new validator
- [x] 7.3 Update `validate_config()` method signature if needed
- [x] 7.4 Add schema version checking
- [x] 7.5 Add schema migration support (for version upgrades)
- [x] 7.6 Maintain backwards compatibility during transition
- [x] 7.7 Add comprehensive type hints

## 8. Add Schema Versioning

- [x] 8.1 Add `version` field to all config schemas
- [x] 8.2 Implement version compatibility checking
- [x] 8.3 Warn when loading config with older schema version
- [x] 8.4 Document schema version upgrade path
- [x] 8.5 Add CLI command `med config validate-schema`
- [x] 8.6 Add CLI command `med config migrate-schema`
- [x] 8.7 Test schema version detection

## 9. Enable Advanced Schema Features

- [x] 9.1 Test `oneOf` for mutually exclusive config options
- [x] 9.2 Test `anyOf` for alternative config formats
- [x] 9.3 Test `if/then/else` for conditional validation
- [x] 9.4 Test `$ref` for schema reuse
- [x] 9.5 Test `definitions` for shared schema fragments
- [x] 9.6 Document advanced features with examples
- [x] 9.7 Add tests for each advanced feature

## 10. Add Custom Format Validators

- [x] 10.1 Register custom format: `duration` (e.g., "5m", "1h")
- [x] 10.2 Register custom format: `file_path` (validate exists)
- [x] 10.3 Register custom format: `url_with_scheme` (http/https only)
- [x] 10.4 Register custom format: `log_level` (DEBUG/INFO/WARNING/ERROR)
- [x] 10.5 Register custom format: `adapter_name` (valid adapter)
- [x] 10.6 Document custom formats in schema guide
- [x] 10.7 Test all custom formats

## 11. Update Configuration Files

- [x] 11.1 Audit all YAML/JSON config files
- [x] 11.2 Add `$schema` reference to each file
- [x] 11.3 Validate all configs with new validator
- [x] 11.4 Fix any validation errors discovered
- [x] 11.5 Add inline comments explaining complex validations
- [x] 11.6 Test config hot-reload with validation

## 12. Add Comprehensive Tests

- [x] 12.1 Test valid configs pass validation
- [x] 12.2 Test invalid configs raise clear errors
- [x] 12.3 Test error messages include JSON pointer
- [x] 12.4 Test schema caching improves performance
- [x] 12.5 Test custom format validators
- [x] 12.6 Test advanced schema features (oneOf, anyOf, if/then)
- [x] 12.7 Test schema version checking
- [x] 12.8 Test migration from custom validator (backwards compat)
- [x] 12.9 Performance test: validate 1000 configs
- [x] 12.10 Integration test with real config files

## 13. Update Documentation

- [x] 13.1 Document JSON Schema usage in `docs/configuration.md`
- [x] 13.2 Add schema authoring guide
- [x] 13.3 Document custom format validators
- [x] 13.4 Add examples of common validation patterns
- [x] 13.5 Document error message interpretation
- [x] 13.6 Update operations runbook with validation commands
- [x] 13.7 Add schema migration guide

## 14. Add Schema Tooling

- [x] 14.1 Create `scripts/validate_all_configs.py`
- [x] 14.2 Create `scripts/generate_config_docs.py` from schemas
- [x] 14.3 Add pre-commit hook for config validation
- [x] 14.4 Add CI check for schema validity
- [x] 14.5 Add JSON Schema IDE integration docs (VSCode, etc.)
- [x] 14.6 Document schema-driven features (autocomplete, tooltips)

## 15. Migration and Rollout

- [x] 15.1 Create migration guide for users
- [x] 15.2 Test migration on staging configs
- [x] 15.3 Run validation on all production configs
- [x] 15.4 Fix any newly discovered config errors
- [ ] 15.5 Deploy to staging with monitoring
- [ ] 15.6 Monitor for config validation errors
- [ ] 15.7 Deploy to production
- [ ] 15.8 Remove custom validator after 30-day validation period
