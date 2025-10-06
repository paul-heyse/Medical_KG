## ADDED Requirements
### Requirement: License Registry YAML Parsing
The license registry SHALL parse YAML inputs into mapping structures, rejecting non-mapping payloads and emitting actionable errors with install guidance.

#### Scenario: Valid license registry YAML
- **GIVEN** a `licenses.yml` file containing `vocabs` and `tiers` mappings
- **WHEN** `LicenseRegistry.from_yaml` is invoked
- **THEN** it SHALL return a populated registry without raising, using structured data

#### Scenario: Invalid license registry YAML
- **WHEN** the YAML loader encounters a scalar or sequence at the root
- **THEN** the registry SHALL raise `LicenseRegistryError` including guidance to supply a mapping
