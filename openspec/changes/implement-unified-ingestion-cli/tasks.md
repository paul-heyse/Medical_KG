# Implementation Tasks

## 1. Design Unified CLI Interface

- [x] 1.1 Document target command structure (`med ingest <adapter> [options]`)
- [x] 1.2 Map all legacy CLI flags to unified flags
- [x] 1.3 Map all modern CLI flags to unified flags
- [x] 1.4 Define backward-compatible flag aliases
- [x] 1.5 Design help text structure and examples
- [x] 1.6 Review design with stakeholders

## 2. Implement Core Unified CLI

- [x] 2.1 Create new `src/Medical_KG/ingestion/cli.py` (replace existing)
- [x] 2.2 Set up Typer app with main `ingest` command
- [x] 2.3 Define `AdapterName` enum for all adapters
- [x] 2.4 Implement `<adapter>` positional argument
- [x] 2.5 Add comprehensive type hints for all parameters
- [x] 2.6 Add module docstring with usage examples

## 3. Implement Batch Processing Options

- [x] 3.1 Add `--batch / --batch-file` option (accepts FILE path)
- [x] 3.2 Add `--output / -o` option (text, json, table)
- [x] 3.3 Add `--resume / --continue` flag for ledger resume
- [x] 3.4 Add `--limit` option for max records
- [x] 3.5 Add `--dry-run` flag for validation only
- [x] 3.6 Add backward-compatible flag aliases

## 4. Implement Auto Mode

- [x] 4.1 Add `--auto` flag for automatic fetching
- [x] 4.2 Support adapter-specific auto mode parameters
- [x] 4.3 Add `--start-date` and `--end-date` for auto filters
- [x] 4.4 Add `--page-size` for auto pagination control
- [x] 4.5 Implement rate limiting for auto mode
- [x] 4.6 Add progress reporting during auto fetch

## 5. Implement Progress and Logging Options

- [x] 5.1 Add `--verbose / -v` flag for detailed output
- [x] 5.2 Add `--quiet / -q` flag for minimal output
- [x] 5.3 Add `--progress` flag for progress bar display
- [x] 5.4 Add `--log-file` option for file logging
- [x] 5.5 Add `--log-level` option (DEBUG, INFO, WARNING, ERROR)
- [x] 5.6 Configure Rich console for beautiful output

## 6. Implement Validation Options

- [x] 6.1 Add `--strict-validation` flag for enhanced checks
- [x] 6.2 Add `--skip-validation` flag (with warning)
- [x] 6.3 Add `--fail-fast` flag to stop on first error
- [x] 6.4 Add `--error-log` option for detailed error output
- [x] 6.5 Show validation summary at end
- [x] 6.6 Support JSON schema validation if available

## 7. Implement Output and Formatting

- [x] 7.1 Use `format_results()` helper from Phase 1
- [x] 7.2 Implement text output format (human-readable)
- [x] 7.3 Implement JSON output format (machine-readable)
- [x] 7.4 Implement table output format (rich tables)
- [x] 7.5 Add `--show-timings` flag for performance metrics
- [x] 7.6 Add `--summary-only` flag for brief output

## 8. Implement Error Handling

- [x] 8.1 Use `format_cli_error()` helper from Phase 1
- [x] 8.2 Handle adapter not found errors
- [x] 8.3 Handle batch file not found errors
- [x] 8.4 Handle malformed NDJSON errors
- [x] 8.5 Handle adapter runtime errors
- [x] 8.6 Add remediation hints for common errors
- [x] 8.7 Set appropriate exit codes (0=success, 1=error, 2=invalid usage)

## 9. Add Comprehensive Help Text

- [x] 9.1 Main command help with overview
- [x] 9.2 Per-adapter help (available adapters list)
- [x] 9.3 Examples section in help text
- [x] 9.4 Add `--version` flag
- [x] 9.5 Add "See also" section pointing to docs
- [x] 9.6 Test help text renders correctly in terminal

## 10. Create Deprecation Delegates

- [x] 10.1 Add `ingest-legacy` command to `Medical_KG.cli`
- [x] 10.2 Show deprecation warning when called
- [x] 10.3 Delegate to unified CLI with flag translation
- [x] 10.4 Log usage for tracking migration progress
- [x] 10.5 Add environment variable to suppress warnings
- [x] 10.6 Document deprecation timeline

## 11. Update Entry Points

- [x] 11.1 Update `pyproject.toml` entry points
- [x] 11.2 Ensure `med ingest` maps to unified CLI
- [x] 11.3 Add `med ingest-legacy` as deprecated alias
- [x] 11.4 Remove old `med-ingest` entry point
- [x] 11.5 Test entry points after installation
- [x] 11.6 Update packaging metadata

## 12. Add Unit Tests

- [x] 12.1 Test command parsing with all flag combinations
- [x] 12.2 Test adapter name validation
- [x] 12.3 Test output format selection
- [x] 12.4 Test error handling for invalid inputs
- [x] 12.5 Test flag aliases work correctly
- [x] 12.6 Test help text generation

## 13. Add Integration Tests

- [x] 13.1 Test batch mode with real NDJSON files
- [x] 13.2 Test auto mode with mock adapter
- [x] 13.3 Test resume functionality end-to-end
- [x] 13.4 Test all output formats produce valid output
- [x] 13.5 Test progress reporting
- [x] 13.6 Test error scenarios (missing files, invalid adapters)
- [x] 13.7 Test deprecated command delegates work

## 14. Update Documentation

- [x] 14.1 Rewrite CLI sections in `docs/ingestion_runbooks.md`
- [x] 14.2 Add migration guide for users
- [x] 14.3 Update `README.md` quick start examples
- [x] 14.4 Update `docs/operations_manual.md` CLI references
- [x] 14.5 Create CLI command reference page
- [x] 14.6 Add troubleshooting section
- [x] 14.7 Document all flags and options
- [x] 14.8 Add examples for common workflows

## 15. Create Migration Tools

- [x] 15.1 Create script to analyze CI configs for old commands
- [x] 15.2 Create script to suggest flag migrations
- [x] 15.3 Add migration checker to CI (warn on old commands)
- [x] 15.4 Create Slack/email announcement template
- [x] 15.5 Update team documentation

## 16. Testing and Validation

- [x] 16.1 Run full test suite - all tests pass
- [x] 16.2 Test with real production data in staging
- [x] 16.3 Compare output with legacy CLI (ensure parity)
- [x] 16.4 Test on different terminal types (TTY, pipe, file)
- [x] 16.5 Test on Windows, Linux, macOS
- [x] 16.6 Performance testing (ensure no regression)

## 17. Rollout and Communication

- [x] 17.1 Announce deprecation timeline (e.g., 3 months)
- [x] 17.2 Update internal documentation
- [x] 17.3 Send migration guide to users
- [x] 17.4 Monitor deprecation warning logs
- [x] 17.5 Deploy to staging first
- [x] 17.6 Deploy to production after validation period
- [x] 17.7 Track adoption metrics
