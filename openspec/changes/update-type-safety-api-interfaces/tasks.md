# Implementation Tasks

## 1. FastAPI Typing Foundations
- [ ] 1.1 Add typed dependency factories for authentication, rate limiting, and config injection.
- [ ] 1.2 Annotate all route handlers with explicit request/response models and return types.
- [ ] 1.3 Replace `Depends(...)` defaults that violate type expectations with typed wrappers.

## 2. Model & Schema Updates
- [ ] 2.1 Refine API Pydantic models (errors, ingest requests, retrieval results) with correct field types.
- [ ] 2.2 Ensure OpenAPI generation runs without mypy suppressions (no `FieldInfo` assignments to typed lists).
- [ ] 2.3 Update briefing API adapter to consume and emit typed DTOs without cast/Any usage.

## 3. Verification
- [ ] 3.1 Run `mypy --strict src/Medical_KG/api src/Medical_KG/briefing src/Medical_KG/app.py` with zero errors.
- [ ] 3.2 Execute FastAPI route integration tests (ingest, retrieve, extraction flows).
- [ ] 3.3 Diff OpenAPI specs to confirm schema stability.
