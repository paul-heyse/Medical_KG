## ADDED Requirements

### Requirement: Type-Safe API Interfaces
API route handlers and briefing integrations SHALL provide fully typed request/response definitions so strict mypy checks succeed across `src/Medical_KG/api`, `src/Medical_KG/briefing`, and `src/Medical_KG/app.py`.

#### Scenario: API strict check
- **WHEN** `mypy --strict src/Medical_KG/api src/Medical_KG/briefing src/Medical_KG/app.py` executes
- **THEN** it SHALL complete without errors
- **AND WHEN** OpenAPI specs are generated
- **THEN** schema generation SHALL succeed without relying on dynamically typed fields
