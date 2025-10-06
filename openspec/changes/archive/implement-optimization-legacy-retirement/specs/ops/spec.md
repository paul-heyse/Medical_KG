## ADDED Requirements
### Requirement: Load-Test Budget Loader
The load-test budget evaluation tooling SHALL parse YAML budget files into mappings before evaluation and raise informative errors when the payload is invalid.

#### Scenario: Valid budget YAML
- **GIVEN** a budget YAML with `defaults` and `profiles`
- **WHEN** the evaluator loads the budget
- **THEN** it SHALL receive a mapping enabling threshold lookups
- **AND** evaluation SHALL execute without attribute errors

#### Scenario: Invalid budget YAML
- **WHEN** the loader encounters a scalar payload
- **THEN** it SHALL raise a `BudgetError` message describing the expected mapping structure
