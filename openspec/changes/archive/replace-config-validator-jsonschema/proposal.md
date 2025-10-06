# Replace Custom Config Validator with jsonschema

## Why

`ConfigValidator` reimplements JSON Schema features poorly:

- Custom validation logic for refs, enums, ranges (~200 lines)
- Must be updated whenever config schema evolves
- Weaker error messages than standard libraries
- Risk of silently skipping unsupported keywords
- No support for advanced schema features (oneOf, anyOf, conditionals)

From `repo_optimization_opportunities.md`: "`ConfigValidator` partially reimplements JSON Schema and has to be updated whenever configs evolve. Maintaining this forked validator increases risk that new keywords or annotations silently skip validation."

## What Changes

- Replace `ConfigValidator` class with `jsonschema` library
- Add schema version tracking and validation
- Improve error messages with JSON pointers
- Support full JSON Schema Draft 7 features
- Reduce custom validation code by ~200 lines
- Document schema versioning strategy

## Impact

- **Affected code**: `src/Medical_KG/config/manager.py` (-200 lines, +50 lines)
- **Benefits**: Better error messages, standard compliance, less maintenance
- **Breaking changes**: None (output format compatible)
- **Risk**: Low - well-tested library, comprehensive test suite
