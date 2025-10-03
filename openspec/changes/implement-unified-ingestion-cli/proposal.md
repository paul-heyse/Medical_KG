# Implement Unified Ingestion CLI Interface

## Why

Building on the shared helpers foundation (`extract-ingestion-cli-shared-helpers`), we now have two CLIs using common code but with different command structures and behaviors. This causes:

**User confusion**:

- Two ways to do the same thing (`med ingest` vs `med-ingest`)
- Different flag names for same operations
- Inconsistent output formats
- Unclear which CLI to use for what

**Operational issues**:

- CI scripts use different commands
- Documentation shows both approaches
- Training materials must cover both
- Bug reports unclear which CLI is affected

**Example inconsistencies** (current state):

```bash
# Legacy CLI
med ingest --source pubmed --batch file.ndjson --resume

# Modern CLI
med-ingest pubmed --batch-file file.ndjson --continue-from-ledger
```

Repository review: "Consolidating both entrypoints on shared helpers would prevent future drift and ensure consistent error handling and resume semantics across tooling."

## What Changes

### Create Unified CLI Entry Point

- Single command: `med ingest <adapter> [options]`
- Uses Typer framework (modern, maintainable)
- Subsumes all functionality from both existing CLIs
- Backward-compatible flag aliases where reasonable

### Standardize Command Structure

```bash
# Unified command structure
med ingest <adapter> [--batch FILE] [--resume] [--output FORMAT]

# Examples
med ingest pubmed --batch articles.ndjson --resume
med ingest umls --batch concepts.ndjson --output json
med ingest clinicaltrials --auto --limit 1000
```

### Implement Feature Parity

- All features from legacy CLI
- All features from modern CLI
- Enhanced validation (from modern)
- Resume semantics (from legacy)
- Auto mode (from legacy)
- Progress reporting (new, from stream-ndjson proposal)

### Migration Path for Users

- Add deprecated command aliases pointing to unified CLI
- `med ingest-legacy` → warns and delegates to `med ingest`
- Environment variable for strict mode (rejects old flags)
- Clear error messages for migrating users

### Consolidated Help and Documentation

- Comprehensive `--help` output
- Examples for common operations
- Migration guide in docs
- Troubleshooting section

## Impact

- **Affected specs**: ingestion (CLI interface changes)
- **Affected code**:
  - `src/Medical_KG/ingestion/cli.py` (replace with unified impl, ~400 lines)
  - `src/Medical_KG/cli.py` (add deprecation delegates, +50 lines)
  - `src/Medical_KG/__main__.py` (update entry points)
  - `tests/ingestion/test_unified_cli.py` (new, ~300 lines)
  - `docs/ingestion_runbooks.md` (rewrite CLI sections, ~100 lines changed)
  - `docs/operations_manual.md` (update CLI references)
  - `README.md` (update quick start examples)
- **Benefits**:
  - **Single way**: One CLI to learn, use, document
  - **Consistency**: Same behavior everywhere
  - **Maintainability**: Single codebase to enhance
  - **Better UX**: Clear, consistent interface
- **Breaking changes**: Old CLI commands deprecated (not removed)
- **Migration burden**: Users must update scripts (with grace period)
- **Risk**: Medium - user-facing changes require careful migration
