# Fix Ruff Configuration and Defensive Formatting

## Why

Two quick wins identified in repository review that prevent issues with minimal effort:

1. **Ruff deprecation warnings**: Project uses deprecated `extend-select` under `[tool.ruff]`, causing warnings on every lint run. Ruff recommends migrating to `[tool.ruff.lint]` table.

2. **Formatter KeyError risks**: `BriefingFormatter` assumes dictionary keys exist (e.g., `section['title']`, `citation['doc_id']`). Missing keys crash HTML/PDF generation. This affects production briefing generation when data sources return partial payloads.

## What Changes

### Ruff Configuration Modernization

- Migrate `pyproject.toml` from `[tool.ruff]` to `[tool.ruff.lint]` table
- Update `extend-select` → `lint.extend-select`
- Remove deprecation warning from all lint runs
- **BREAKING**: None (backward compatible)

### Defensive Formatter Guards

- Add `.get()` guards in `BriefingFormatter.format_*` methods
- Provide sensible defaults for missing keys:
  - `section['title']` → `section.get('title', 'Untitled Section')`
  - `citation['doc_id']` → `citation.get('doc_id', 'Unknown')`
  - `item['content']` → `item.get('content', '')`
- Add tests for partial payload scenarios
- **BREAKING**: None (graceful degradation)

## Impact

- **Affected specs**: None (tooling only)
- **Affected code**:
  - `pyproject.toml` (ruff config migration, ~5 lines)
  - `src/Medical_KG/briefing/formatters.py` (~15 `.get()` additions)
  - `tests/briefing/test_formatters.py` (+30 lines for partial data tests)
- **Benefits**:
  - Clean lint runs (no deprecation warnings)
  - Robust briefing generation (no KeyError crashes)
  - Better error messages for incomplete data
- **Risk**: Low (both changes are defensive)
