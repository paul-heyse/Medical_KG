# Runbook 08 – Briefing Generation Troubleshooting

## Summary

Diagnose and remediate incomplete or partially rendered briefing exports. Applies to
Markdown, HTML, PDF, and DOCX outputs generated via `BriefingFormatter`.

## Preconditions

- Access to the briefing payload stored in S3 or the retrieval cache.
- Python environment with `Medical_KG` tooling available (`./.venv`).
- Ability to contact the ingestion on-call if upstream data gaps are detected.

## Steps

1. **Reproduce locally**
   - Run `python -m Medical_KG.briefing.preview <payload.json>` to render all formats.
   - Confirm whether placeholders such as "Untitled Briefing" or "Unknown" appear.
2. **Inspect payload structure**
   - Verify each section is a mapping with an `items` sequence.
   - Ensure each item provides either `summary` or `description` text.
   - Check that citations include `doc_id` and `quote` fields.
3. **Leverage formatter defaults**
   - Missing titles automatically fall back to `Untitled Section`.
   - Missing citation identifiers render as `Unknown` with a count of `0`.
   - Empty summaries are omitted from exports; add context upstream if needed.
4. **Patch upstream data**
   - For ingestion gaps, update the source dataset and rerun the adapter.
   - For analyst-authored briefs, edit the briefing draft in the UI and regenerate.
5. **Escalate if placeholders persist**
   - Collect the payload and generated output.
   - Page the ingestion on-call with details about the missing metadata.

## Verification

- Regenerated briefing outputs no longer display placeholder text.
- `pytest tests/briefing/test_formatters.py -k partial` passes locally.
- Analysts confirm the deliverable contains the expected sections and citations.
