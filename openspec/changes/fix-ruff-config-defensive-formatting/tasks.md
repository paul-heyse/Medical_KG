# Implementation Tasks

## 1. Modernize Ruff Configuration

- [ ] 1.1 Update `pyproject.toml` to use `[tool.ruff.lint]` table
- [ ] 1.2 Migrate `extend-select` to `lint.extend-select`
- [ ] 1.3 Verify `ruff check src tests` runs without deprecation warnings
- [ ] 1.4 Update any CI scripts that reference old config format

## 2. Add Defensive Guards to BriefingFormatter

- [ ] 2.1 Audit `formatters.py` for direct dictionary access patterns
- [ ] 2.2 Replace `section['title']` with `section.get('title', 'Untitled Section')`
- [ ] 2.3 Replace `citation['doc_id']` with `citation.get('doc_id', 'Unknown')`
- [ ] 2.4 Replace `citation['citation_count']` with `citation.get('citation_count', 0)`
- [ ] 2.5 Replace `item['content']` with `item.get('content', '')`
- [ ] 2.6 Add guards for all other dictionary accesses in format methods

## 3. Add Tests for Partial Payloads

- [ ] 3.1 Create test fixtures for briefings with missing fields
- [ ] 3.2 Test `format_html()` with partial sections (missing title)
- [ ] 3.3 Test `format_html()` with partial citations (missing doc_id)
- [ ] 3.4 Test `format_html()` with empty content items
- [ ] 3.5 Test `format_pdf()` with same partial scenarios
- [ ] 3.6 Verify graceful degradation (no crashes, sensible output)

## 4. Documentation

- [ ] 4.1 Document default values in formatter docstrings
- [ ] 4.2 Add "Handling Partial Data" section to briefing docs
- [ ] 4.3 Update operations runbook with troubleshooting for incomplete briefs

## 5. Validation

- [ ] 5.1 Run `ruff check src tests` - verify no warnings
- [ ] 5.2 Run `pytest tests/briefing/` - all tests pass
- [ ] 5.3 Test with production briefing data to ensure no regressions
- [ ] 5.4 Verify HTML/PDF generation works with partial payloads
