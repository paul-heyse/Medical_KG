# Ingestion Operations Runbook

## API Credential Acquisition

- **NCBI E-utilities** – request an API key via the [NCBI account portal](https://www.ncbi.nlm.nih.gov/account/). The key raises rate limits from 3 RPS to 10 RPS. Store in `NCBI_EUTILS_API_KEY`.
- **openFDA** – generate an application token from the [openFDA developer console](https://open.fda.gov/apis/authentication/). Configure `OPENFDA_API_KEY` to unlock 240 RPM.
- **NICE Syndication** – email api@nice.org.uk with intended use; place the key in `NICE_API_KEY` and retain licence compliance metadata.
- **UMLS / Terminology Services** – request a [UMLS Metathesaurus key](https://uts.nlm.nih.gov/) and set `UMLS_API_KEY` for authenticated requests.
- **RxNav** – register at https://rxnav.nlm.nih.gov/ for `RXNAV_APP_ID`/`RXNAV_APP_KEY`.
- **CDC / WHO open data** – configure `CDC_SOCRATA_APP_TOKEN` and `WHO_GHO_APP_TOKEN` for higher throttling tiers.

## Runbooks for Common Failures

| Scenario | Detection | Mitigation |
| --- | --- | --- |
| Rate-limit exceeded | HTTP 429 with `Retry-After` header; ledger transitions to `*_failed` | Backoff using exponential retry (already enabled). If failure persists > 15m, reduce concurrency or request elevated tier. |
| Auth expired | 401/403 responses; ledger entry metadata includes `reason="auth"` | Rotate credentials, update `.env`, restart ingestion job. |
| Source schema drift | ValidationError raised in adapter `validate()` step; ledger records `schema_failed` | Capture payload sample, update adapter parser/tests, regenerate fixtures, and redeploy. |
| Network outage | `httpx.ConnectError` recorded; ledger state `network_failed` | Retries handled automatically. For sustained incidents > 1h, pause jobs and notify operations. |

## Batch & Auto Modes

- The CLI (`med ingest`) supports `--auto` to stream ingested `doc_id`s and advance the ledger to `auto_done`.
- Provide `--batch path.ndjson` with one JSON object per line to run targeted re-ingestion campaigns.

## Licensing Requirements

- **UMLS** – downstream use requires the annual UMLS acceptance; document user accounts with the NLM.
- **SNOMED CT** – ensure the organisation holds a national release licence before enabling the Snowstorm adapter.
- **MedDRA** – adverse event enrichment requires an active subscription; verify `meddra_version` metadata before distribution.
- **NICE content** – honour `licence` metadata (e.g., `OpenGov`, `CC-BY-ND`) and restrict redistribution when required.
