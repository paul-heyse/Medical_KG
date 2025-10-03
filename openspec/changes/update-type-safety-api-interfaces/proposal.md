## Why
FastAPI interfaces and briefing entry points contribute 47 strict mypy errors (missing annotations, Depends defaults, typed responses). This prevents the API layer from meeting the `type-safety` enforcement gate and increases runtime risk.

## What Changes
- Introduce typed FastAPI dependency wrappers and response models that avoid `Any` defaults.
- Annotate API route handlers, background tasks, and Pydantic response models.
- Update briefing API/service glue code to pass typed DTOs to the API layer.
- Add stubs or helper protocols where third-party integrations (FastAPI, Starlette) lack explicit typing.

## Impact
- Affected specs: `type-safety`
- Affected code: `src/Medical_KG/api/*`, `src/Medical_KG/briefing/*`, `src/Medical_KG/app.py`, relevant tests.
- Risks: API schema regressions; mitigated by OpenAPI snapshot verification and integration tests.
