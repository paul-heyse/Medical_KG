# Ingestion Operations Runbook

## API Credential Acquisition

- **NCBI E-utilities** – request an API key via the [NCBI account portal](https://www.ncbi.nlm.nih.gov/account/). The key raises rate limits from 3 RPS to 10 RPS. Store in `NCBI_EUTILS_API_KEY`.
- **openFDA** – generate an application token from the [openFDA developer console](https://open.fda.gov/apis/authentication/). Configure `OPENFDA_API_KEY` to unlock 240 RPM.
- **NICE Syndication** – email <api@nice.org.uk> with intended use; place the key in `NICE_API_KEY` and retain licence compliance metadata.
- **UMLS / Terminology Services** – request a [UMLS Metathesaurus key](https://uts.nlm.nih.gov/) and set `UMLS_API_KEY` for authenticated requests.
- **RxNav** – register at <https://rxnav.nlm.nih.gov/> for `RXNAV_APP_ID`/`RXNAV_APP_KEY`.
- **CDC / WHO open data** – configure `CDC_SOCRATA_APP_TOKEN` and `WHO_GHO_APP_TOKEN` for higher throttling tiers.

## Runbooks for Common Failures

| Scenario | Detection | Mitigation |
| --- | --- | --- |
| Rate-limit exceeded | HTTP 429 with `Retry-After` header; ledger transitions to `*_failed` | Backoff using exponential retry (already enabled). If failure persists > 15m, reduce concurrency or request elevated tier. |
| Auth expired | 401/403 responses; ledger entry metadata includes `reason="auth"` | Rotate credentials, update `.env`, restart ingestion job. |
| Source schema drift | ValidationError raised in adapter `validate()` step; ledger records `schema_failed` | Capture payload sample, update adapter parser/tests, regenerate fixtures, and redeploy. |
| Network outage | `httpx.ConnectError` recorded; ledger state `network_failed` | Retries handled automatically. For sustained incidents > 1h, pause jobs and notify operations. |

## Unified Ingestion CLI

- Entry point: `med ingest <adapter> [options]` with a positional adapter argument validated against the registry.
- Format selection: `--output text|json|table`, plus `--summary-only` for log-friendly output and `--show-timings` for runtime metrics.
- Batch orchestration: `--batch path.ndjson` (chunked automatically with `--chunk-size`), `--id` for targeted document replays, and `--limit` to cap records.
- Resume & auto pipelines: `--resume`, `--auto`, `--page-size`, `--start-date`, `--end-date`, and `--rate-limit` control long-running fetches.
- Validation toggles: `--strict-validation`, `--skip-validation`, `--fail-fast`, `--dry-run`, and the new `--schema schema.json` guardrail to validate NDJSON rows against JSON Schema when available.
- Logging & UX: `--progress/--no-progress`, `--quiet`, `--verbose`, `--log-level`, `--log-file`, and `--error-log` tailor operator feedback.
- Help output: `med ingest --help` renders an overview, dynamic adapter list, markdown-formatted examples, and links to the migration + reference docs.
- Deprecation path: `med ingest-legacy` delegates with a warning; set `MEDICAL_KG_SUPPRESS_INGEST_DEPRECATED=1` to silence the notice during scripted migrations.

### Command Overview & Examples

```bash
# Run a batch ingest with schema validation and resume semantics
med ingest demo --batch params.ndjson --schema schemas/demo.json --resume

# Stream auto-mode results to downstream tooling with JSON output
med ingest umls --auto --limit 1000 --output json --show-timings

# Perform a dry-run validation (no adapter execution) with a specific ID set
med ingest nice --id guideline-123 --id guideline-456 --dry-run --summary-only
```

Running `med ingest --help` lists all adapters discovered in the registry and highlights the most common workflows. The "See also" epilog links directly to this runbook, the command reference, and the migration guide for quick onboarding.

## Batch & Auto Modes

- The CLI (`med ingest`) supports `--auto` to stream ingested `doc_id`s and advance the ledger to `auto_done`.
- Provide `--batch path.ndjson` with one JSON object per line to run targeted re-ingestion campaigns.
- Large NDJSON payloads are processed incrementally using a configurable `--chunk-size` (default 1000 records). The CLI loads
  only a single chunk in memory, preventing OOM events for million-record replays.
- Progress feedback is emitted via a terminal progress bar that tracks completed records, ETA, and throughput whenever the `rich`
  dependency is available. Disable it with `--quiet` for log-friendly output or when running in non-interactive shells.
- When `--auto` is active the CLI emits chunk-level doc ID batches immediately after each chunk completes, so monitoring systems
  can tail progress without waiting for the entire dataset.

### Shared CLI Helper Module

- Import `Medical_KG.ingestion.cli_helpers` to share ingestion orchestration logic between the unified CLI and automation scripts.
- `load_ndjson_batch(path_or_stream, *, progress=None)` parses NDJSON safely, skips blank lines, and optionally reports a running count for progress bars.
- `invoke_adapter_sync(source, ledger, params=None, resume=False)` resolves the adapter, manages the shared HTTP client, and returns `PipelineResult` summaries for each parameter set.
- `handle_ledger_resume(ledger_path_or_instance, candidate_doc_ids=None)` inspects the ingestion ledger to compute resume statistics (skipped vs. pending) and provides the filtered ID list for dry-run previews.
- `format_cli_error(exc, prefix="Error", remediation=None)` renders coloured, user-friendly errors that can be reused across CLIs and scripts.
- `format_results(results, output_format="jsonl")` produces consistent summaries for automation (JSONL) or operator dashboards (text/table) and exposes aggregated counts.

## Streaming Pipelines & Memory Guardrails

- `IngestionPipeline.iter_results()` exposes an async iterator that yields `Document` instances as soon as adapters complete
  parsing/validation. Use it for long-running replays to surface telemetry without materialising the full result set.
- Both the CLI and orchestration helpers reuse a single async HTTP client per pipeline invocation and close it eagerly even if
  iteration stops early, avoiding dangling sockets during aborts.
- Memory remains O(1) with respect to batch size because only the active chunk (or in-flight document) is retained in process
  memory. Expect <150MB RSS for million-row NDJSON files when using the default chunk size.
- For operational audits capture `rich` progress output and ledger deltas; both reflect chunk boundaries which simplifies
  diagnosing partial failures.

## Licensing Requirements

- **UMLS** – downstream use requires the annual UMLS acceptance; document user accounts with the NLM.
- **SNOMED CT** – ensure the organisation holds a national release licence before enabling the Snowstorm adapter.
- **MedDRA** – adverse event enrichment requires an active subscription; verify `meddra_version` metadata before distribution.
- **NICE content** – honour `licence` metadata (e.g., `OpenGov`, `CC-BY-ND`) and restrict redistribution when required.

## HTTP Client Response Types

All HTTP-backed adapters call `AsyncHttpClient` (via `HttpAdapter`) which now returns typed wrapper objects instead of bare
`httpx.Response` instances. Each wrapper exposes the payload through an explicit attribute so mypy can enforce the correct
access pattern.

| Client method | Wrapper | Primary accessor | When to use |
| ------------- | ------- | ---------------- | ----------- |
| `await client.get_json(...)` | `JsonResponse[T]` | `.data` | JSON APIs that return mappings or arrays |
| `await client.get_text(...)` | `TextResponse` | `.text` | Endpoints that respond with HTML, XML, or plaintext |
| `await client.get_bytes(...)` | `BytesResponse` | `.content` | Binary payloads such as PDFs or compressed archives |
| `client.stream(...)` | `httpx.Response` | `.aiter_bytes()` / `.aiter_text()` | Streaming downloads (wrap in typed helpers before parsing) |

### JsonResponse

`JsonResponse` wraps a decoded JSON payload together with metadata about the request. Treat `.data` as the structured JSON
object and keep it typed via `TypedDict` or helper Protocols:

```python
from typing import Mapping, Sequence, TypedDict, cast

from Medical_KG.ingestion.http_client import JsonResponse


class PubMedEnvelope(TypedDict):
    result: Mapping[str, Mapping[str, object]]
    uids: Sequence[str]


response: JsonResponse[PubMedEnvelope] = cast(
    JsonResponse[PubMedEnvelope],
    await self.client.get_json(f"{self.base_url}/esummary.fcgi", params={"id": pmid}),
)
summary = response.data["result"][pmid]
```

Use `.url` and `.status_code` on the wrapper for logging without reformatting the payload.

### TextResponse

`TextResponse` provides the decoded body via `.text`. Use it when you only need textual content (HTML, XML, CSV) and keep the
parsing logic type-safe:

```python
text_response = await self.client.get_text(feed_url)
document = self._parse_xml(text_response.text)
```

### BytesResponse

`BytesResponse` exposes the raw byte stream through `.content`. It is the right choice for binary downloads, allowing you to
feed the bytes into PDF parsers or compression libraries without extra casting:

```python
pdf_response = await self.client.get_bytes(pdf_url)
self._store_pdf(set_id, pdf_response.content)
```

### When wrappers are returned

- `HttpAdapter.fetch_json()`/`get_json()` → `JsonResponse`
- `HttpAdapter.fetch_text()`/`get_text()` → `TextResponse`
- `HttpAdapter.fetch_bytes()`/`get_bytes()` → `BytesResponse`

Each helper returns the correctly typed attribute so downstream code interacts with `dict`, `str`, or `bytes` without
touching the wrapper object again.

## Integration Examples with Typed Responses

### Complete adapter example

```python
from __future__ import annotations

from typing import Any, AsyncIterator, Mapping, Sequence, TypedDict, cast

from Medical_KG.compat.httpx import HTTPError
from Medical_KG.ingestion.adapters.base import AdapterFetchError
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import JSONMapping, JSONValue, is_umls_payload


class UmlsPayload(TypedDict):
    cui: str
    title: str
    atoms: Sequence[JSONMapping]


class UmlsAdapter(HttpAdapter[JSONMapping]):
    async def fetch(self) -> AsyncIterator[JSONMapping]:
        async for cui in self._iter_concept_ids():
            response = await self.client.get_json(f"{self.base_url}/content/current/CUI/{cui}")
            yield cast(JSONMapping, response.data)

    def parse(self, raw: JSONMapping) -> Document:
        payload: UmlsPayload = {
            "cui": raw["ui"],
            "title": raw.get("name", ""),
            "atoms": cast(Sequence[JSONMapping], raw.get("atoms", [])),
        }
        return Document(
            doc_id=f"umls:{payload['cui']}",
            source="umls",
            content=payload["title"],
            metadata={"cui": payload["cui"]},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        raw = document.raw
        assert is_umls_payload(raw), "UMLSAdapter produced wrong payload"
```

Every block above type-checks with `./.venv/bin/python -m mypy --strict` when copied into a module, ensuring on-call engineers
can rely on the patterns during incidents.

### Error handling with response wrappers

```python
try:
    response = await self.client.get_json(f"{self.base_url}/studies/{nct_id}")
except HTTPError as exc:
    raise AdapterFetchError(f"Failed to fetch {nct_id}") from exc

study = cast(JSONMapping, response.data)
```

Catch `HTTPError` (exposed through `Medical_KG.compat.httpx`) to surface actionable errors in the ledger while retaining the
typed payload.

### Async iteration patterns

```python
async def iter_pages(self) -> AsyncIterator[JSONMapping]:
    page = 1
    while True:
        response = await self.client.get_json(self._page_url(page))
        payload = cast(Mapping[str, JSONValue], response.data)
        items = payload.get("results", [])
        if not items:
            break
        for item in items:
            yield cast(JSONMapping, item)
        page += 1
```

The wrapper is consumed exactly once per request, keeping pagination code predictable and type-safe.

## Troubleshooting Typed Response Migration

### "JsonResponse object is not subscriptable"

- **Cause** – legacy code expected `httpx.Response` and tried `response["key"]`.
- **Fix** – access `.data` (or call `fetch_json()` to receive a `JSONMapping`). If you need a narrower type, wrap the payload in
  a `TypedDict` and use `typing.cast`.

```python
payload = cast(MyEnvelope, response.data)
record = payload["result"][0]
```

### "TextResponse has no attribute 'strip'"

- **Cause** – the wrapper instance itself is not a `str`.
- **Fix** – use `response.text.strip()` or call `fetch_text()` which returns the string directly.

```python
text = await self.fetch_text(feed_url)
clean = text.strip()
```

### Migration quick reference

| Legacy pattern | Replacement | Notes |
| -------------- | ----------- | ----- |
| `payload = response["result"]` | `payload = response.data["result"]` | Access the decoded JSON mapping |
| `text = response` | `text = response.text` | Wrapper exposes `.text`; or use `fetch_text()` |
| `blob = response` | `blob = response.content` | Use `.content` for binary payloads |
| `response.raise_for_status()` | `await self.client.get_json(...)` | The client raises automatically; catch `HTTPError` for retries |

## Cross references

- [TypedDict contracts guide](ingestion_typed_contracts.md) – payload construction patterns.
- [Type safety guidelines](type_safety.md) – project-wide typing conventions.
- [HTTP client implementation](../src/Medical_KG/ingestion/http_client.py) – authoritative API surface for response wrappers.

Re-run `./.venv/bin/python -m mypy --strict` on any adapter that adopts these examples to guarantee the migration stayed
type-safe.
