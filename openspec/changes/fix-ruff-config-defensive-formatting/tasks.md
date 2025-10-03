# Implementation Tasks

## 1. Modernize Ruff Configuration

- [x] 1.1 Update `pyproject.toml` to use `[tool.ruff.lint]` table
- [x] 1.2 Migrate `extend-select` to `lint.extend-select`
- [x] 1.3 Verify `ruff check src tests` runs without deprecation warnings
- [x] 1.4 Update any CI scripts that reference old config format

## 2. Add Defensive Guards to BriefingFormatter

- [x] 2.1 Audit `formatters.py` for direct dictionary access patterns
- [x] 2.2 Replace `section['title']` with `section.get('title', 'Untitled Section')`
- [x] 2.3 Replace `citation['doc_id']` with `citation.get('doc_id', 'Unknown')`
- [x] 2.4 Replace `citation['citation_count']` with `citation.get('citation_count', 0)`
- [x] 2.5 Replace `item['content']` with `item.get('content', '')`
- [x] 2.6 Add guards for all other dictionary accesses in format methods

## 3. Add Tests for Partial Payloads

- [x] 3.1 Create test fixtures for briefings with missing fields
- [x] 3.2 Test `format_html()` with partial sections (missing title)
- [x] 3.3 Test `format_html()` with partial citations (missing doc_id)
- [x] 3.4 Test `format_html()` with empty content items
- [x] 3.5 Test `format_pdf()` with same partial scenarios
- [x] 3.6 Verify graceful degradation (no crashes, sensible output)

## 4. Documentation

- [x] 4.1 Document default values in formatter docstrings
- [x] 4.2 Add "Handling Partial Data" section to briefing docs
- [x] 4.3 Update operations runbook with troubleshooting for incomplete briefs

## 5. Validation

- [x] 5.1 Run `ruff check src tests` - verify no warnings
- [x] 5.2 Run `pytest tests/briefing/` - all tests pass
- [x] 5.3 Test with production briefing data to ensure no regressions
- [x] 5.4 Verify HTML/PDF generation works with partial payloads
