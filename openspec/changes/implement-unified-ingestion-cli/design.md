# Unified Ingestion CLI Design

## Context

The Medical_KG project currently maintains two parallel ingestion CLIs with overlapping functionality but different interfaces. After completing `extract-ingestion-cli-shared-helpers`, both CLIs use common helper functions, but users still face:

- Two command structures to learn
- Inconsistent flag names and behaviors
- Unclear which CLI to use
- Duplicated documentation and training

This proposal creates a single, unified CLI that supersedes both implementations while maintaining backward compatibility during a migration period.

## Goals

- **Single CLI interface**: One command structure for all ingestion operations
- **Feature parity**: All features from both legacy and modern CLIs
- **Backward compatibility**: Deprecated aliases for smooth migration
- **Better UX**: Clear, consistent, well-documented interface
- **Maintainability**: Single codebase to enhance and test

## Non-Goals

- **Not removing legacy CLI immediately**: Deprecation timeline allows migration
- **Not changing adapter implementations**: Only CLI interface affected
- **Not changing output file formats**: NDJSON, ledger formats unchanged
- **Not changing HTTP client or ingestion core**: Only CLI layer

## Decisions

### Decision 1: Typer Framework

**Choice**: Use Typer (modern CLI) as the foundation

**Rationale**:

- Better type safety (integrates with mypy --strict)
- Automatic help generation from type hints
- Rich console support (progress bars, colors)
- Better error messages
- More maintainable codebase
- Active development and community

**Alternatives considered**:

- Click (legacy CLI uses this): Less type-safe, more boilerplate
- argparse: Standard library but verbose, limited features
- Building from scratch: Too much effort, reinventing wheel

### Decision 2: Command Structure

**Choice**: `med ingest <adapter> [options]`

**Rationale**:

- Adapter name as positional arg is intuitive
- Follows common CLI patterns (e.g., `git clone <repo>`)
- Enables tab completion for adapter names
- Clear hierarchy: command → adapter → options

**Example**:

```bash
med ingest pubmed --batch articles.ndjson --resume
med ingest umls --auto --limit 1000
```

**Alternatives considered**:

- `med ingest --adapter pubmed ...`: Verbose, less intuitive
- `med pubmed ingest ...`: Non-standard, breaks CLI hierarchy
- Separate commands per adapter: Too many entry points

### Decision 3: Flag Naming Conventions

**Choice**: Use consistent, descriptive flag names with short aliases

| Purpose | Flag | Short | Legacy Equivalent | Modern Equivalent |
|---------|------|-------|-------------------|-------------------|
| Batch file | `--batch` | `-b` | `--batch` | `--batch-file` |
| Resume | `--resume` | `-r` | `--resume` | `--continue-from-ledger` |
| Output format | `--output` | `-o` | N/A | `--format` |
| Auto mode | `--auto` | N/A | `--auto` | N/A |
| Verbose | `--verbose` | `-v` | `--verbose` | `-v` |
| Limit | `--limit` | `-n` | `--limit` | `--max-records` |

**Rationale**:

- Short flags for frequently used options
- Descriptive long flags for clarity
- Backward-compatible where possible

### Decision 4: Deprecation Strategy

**Choice**: Soft deprecation with 3-month migration period

**Timeline**:

1. **Month 0**: Unified CLI released, warnings added
2. **Month 1**: Migration guide published, CI updated
3. **Month 2**: Deprecation notices in terminal output
4. **Month 3**: Legacy commands removed (next major version)

**Rationale**:

- Gradual migration reduces user disruption
- Warnings provide clear migration path
- 3 months allows CI/CD updates
- Major version bump signals breaking change

**Alternatives considered**:

- Immediate removal: Too disruptive, breaks scripts
- Permanent dual CLI: Maintenance burden continues
- 6+ month timeline: Unnecessarily long

### Decision 5: Output Format Strategy

**Choice**: Three output formats with consistent structure

1. **Text** (default): Human-readable, colored, progress bars
2. **JSON**: Machine-readable, for CI/scripts
3. **Table**: Structured, for reports

**Format structure**:

```python
{
  "adapter": "pubmed",
  "batch_file": "articles.ndjson",
  "started_at": "2025-10-03T12:00:00Z",
  "completed_at": "2025-10-03T12:05:30Z",
  "duration_seconds": 330,
  "results": {
    "total": 1000,
    "success": 985,
    "failed": 15,
    "skipped": 0
  },
  "errors": [...]
}
```

**Rationale**:

- Text for developers using terminal
- JSON for CI integration
- Table for documentation/reports
- Consistent schema across formats

### Decision 6: Progress Reporting

**Choice**: Use Rich library for progress bars and live displays

**Features**:

- Overall progress bar (X/N records)
- Current record being processed
- Success/failure counters
- ETA calculation
- Auto-hide in non-TTY environments

**Rationale**:

- Rich is already a dependency
- Better UX for long-running operations
- Automatic TTY detection
- No output pollution for pipes

### Decision 7: Error Handling Hierarchy

**Choice**: Three-tier error handling

1. **User errors** (exit code 2): Invalid flags, missing files
   - Show usage hint
   - Point to `--help`
   - Don't log as system errors

2. **Data errors** (exit code 1): Malformed NDJSON, validation failures
   - Show affected records
   - Continue processing if `--fail-fast` not set
   - Log for debugging

3. **System errors** (exit code 1): Network failures, adapter crashes
   - Show full stack trace if `--verbose`
   - Log for debugging
   - Fail fast by default

**Rationale**:

- Clear distinction between error types
- Appropriate remediation hints
- Scriptable (exit codes)
- Debuggable (verbose mode)

## Risks / Trade-offs

### Risk 1: User Disruption

**Risk**: Users must update scripts and CI configs

**Mitigation**:

- Soft deprecation with warnings
- Backward-compatible delegates
- Clear migration guide
- 3-month grace period
- Automated migration checker

**Trade-off accepted**: Short-term disruption for long-term consistency

### Risk 2: Feature Parity Gaps

**Risk**: Missing features from one CLI not noticed until deployment

**Mitigation**:

- Comprehensive feature matrix (legacy vs modern)
- Integration tests verifying all legacy features work
- Staging deployment with user testing
- Beta period before production

### Risk 3: Performance Regression

**Risk**: Rich console features slow down CLI

**Mitigation**:

- Benchmark against legacy CLI
- Auto-disable Rich in non-TTY (pipes)
- Add `--no-progress` flag for minimal overhead
- Test with large batches (10k+ records)

### Risk 4: Documentation Debt

**Risk**: Old documentation persists, confuses users

**Mitigation**:

- Search codebase for CLI examples
- Update all docs atomically
- Add redirects from old command docs
- Deprecation notices in old docs

## Migration Plan

### Phase 1: Development (Week 1-2)

1. Implement unified CLI in staging branch
2. Add comprehensive tests
3. Update documentation
4. Internal testing

### Phase 2: Staging Deployment (Week 3)

1. Deploy to staging environment
2. Run smoke tests
3. User acceptance testing
4. Collect feedback

### Phase 3: Beta Release (Week 4)

1. Release with deprecation warnings
2. Publish migration guide
3. Monitor warning logs
4. Update internal CI/CD

### Phase 4: Production Release (Week 5)

1. Deploy to production
2. Monitor adoption metrics
3. Support user migration
4. Track deprecation usage

### Phase 5: Deprecation (Month 3)

1. Remove legacy entry points
2. Clean up delegates
3. Final documentation update
4. Close migration issues

## Open Questions

1. **Should we support custom adapter plugins via CLI?**
   - Current scope: Built-in adapters only
   - Future: Could add `--adapter-module` for custom adapters

2. **Should progress reporting be opt-in or opt-out?**
   - Proposal: Auto-enable for TTY, disable for pipes
   - Can override with `--progress` / `--no-progress`

3. **How to handle platform-specific features?**
   - Example: Windows color support, macOS notifications
   - Proposal: Graceful degradation, test on all platforms

4. **Should we version the CLI separately from the library?**
   - Proposal: No, follow library versioning
   - CLI deprecations = major version bump

## Success Criteria

- [ ] Single `med ingest` command supports all use cases
- [ ] All legacy CLI features available
- [ ] All modern CLI features available
- [ ] Integration tests pass for both workflows
- [ ] Documentation complete and accurate
- [ ] Zero regressions in functionality
- [ ] Migration guide published
- [ ] Adoption tracking in place
