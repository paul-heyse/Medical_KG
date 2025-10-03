# Briefing Formatter Overview

The briefing formatter converts dossier payloads into Markdown, HTML, PDF, and DOCX
outputs for downstream delivery. The formatter accepts dictionaries sourced from the
retrieval and synthesis pipelines, tolerating partially populated records so analysts can
preview work-in-progress briefs without manual cleanup.

## Handling Partial Data

When payloads omit optional metadata, the formatter now substitutes defensive defaults to
keep exports readable:

- Missing topics render as **"Untitled Briefing"**.
- Missing section titles render as **"Untitled Section"**.
- Missing citation identifiers render as **"Unknown"** with a citation count defaulting to `0`.
- Missing summaries or descriptions skip bullet output instead of raising errors.
- Missing bibliography entries are ignored; malformed counts are coerced to integers.

These defaults are consistent across Markdown, HTML, PDF, and DOCX renderers. Test
coverage under `tests/briefing/test_formatters.py` asserts that each formatter handles
partial payloads without raising exceptions and that fallback values are present in the
resulting documents.

## Operational Notes

- When investigators spot placeholder labels (e.g., "Untitled Section"), they should trace
  the originating ingestion record to supply the missing metadata.
- PDF and DOCX exports omit empty entries; analysts can safely share the output without
  exposing placeholder bullets.
- The formatter remains deterministic—identical payloads will always yield identical
  outputs regardless of missing fields.
