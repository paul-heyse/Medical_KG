# Ingestion Operations Runbook

## API Credential Acquisition

- **NCBI E-utilities** – request an API key via the [NCBI account portal](https://www.ncbi.nlm.nih.gov/account/). The key raises rate limits from 3 RPS to 10 RPS. Store in `NCBI_EUTILS_API_KEY`.
- **openFDA** – generate an application token from the [openFDA developer console](https://open.fda.gov/apis/authentication/). Configure `OPENFDA_API_KEY` to unlock 240 RPM.
- **NICE Syndication** – email <api@nice.org.uk> with intended use; place the key in `NICE_API_KEY` and retain licence compliance metadata.
- **UMLS / Terminology Services** – request a [UMLS Metathesaurus key](https://uts.nlm.nih.gov/) and set `UMLS_API_KEY` for authenticated requests.
- **RxNav** – register at <https://rxnav.nlm.nih.gov/> for `RXNAV_APP_ID`/`RXNAV_APP_KEY`.
- **CDC / WHO open data** – configure `CDC_SOCRATA_APP_TOKEN` and `WHO_GHO_APP_TOKEN` for higher throttling tiers.

## Ledger State Machine

- **States** – ingestion transitions are constrained to the `LedgerState` enum (`pending → fetching → fetched → parsing → parsed → validating → validated → ir_building → ir_ready → embedding → indexed → completed`). Error branches move to `failed`, optionally cycling through `retrying`. Terminal outcomes are `completed`, `failed`, and `skipped`.
- **Transition graph** – invalid edges raise `InvalidStateTransition` and increment the `med_ledger_errors_total` counter. The ASCII diagram below mirrors the implementation in `Medical_KG.ingestion.ledger`:

```
[PENDING] -> [FETCHING] -> [FETCHED] -> [PARSING] -> [PARSED] -> [VALIDATING]
                                                              |
                                                              v
                                                         [VALIDATED]
                                                              |
                                                              v
[IR_BUILDING] -> [IR_READY] -> [EMBEDDING] -> [INDEXED] -> [COMPLETED]

Retry loop: any retryable state -> [RETRYING] -> [FETCHING]
Failure: any stage can fall back to [FAILED]
```

- **State semantics** – PDF ingestion emits `ir_building` during MinerU execution, `ir_ready` when artifacts are persisted, and `embedding` when downstream processors are triggered. Ledger transitions must use the `LedgerState` enum; attempting to pass raw strings raises a `TypeError`.

### Snapshots and Compaction

- Snapshots live beside the ledger at `ledger.snapshots/snapshot-<timestamp>.json` and contain the full document state plus audit history. The append-only JSONL file now acts purely as a delta log.
- `IngestionLedger` checks for a snapshot on initialisation, then applies the delta log, yielding O(1) startup time regardless of historical volume.
- Automatic compaction runs daily (configurable via `auto_snapshot_interval`) and truncates the delta log after a successful snapshot. Manual compaction is available via `med ledger compact`.
- Previous snapshots are rotated automatically, retaining the most recent seven by default.

### CLI Utilities

- `med ledger stats` prints the live document count per state, matching the Prometheus gauge `med_ledger_documents_by_state`.
- `med ledger stuck --hours 12` surfaces documents lingering in non-terminal states beyond the threshold and logs a warning for alerting systems.
- `med ledger history <doc_id>` renders the structured audit timeline pulled from the JSONL delta log.

### Metrics and Alerting

- Counters: `med_ledger_state_transitions_total` (labelled by `from_state`/`to_state`), `med_ledger_initialization_total` (snapshot vs. full load), `med_ledger_errors_total` (invalid transitions, serialization failures).
- Gauges: `med_ledger_documents_by_state`, `med_ledger_stuck_documents` (non-terminal backlog).
- Histogram: `med_ledger_state_duration_seconds` observes time spent in each state prior to transition.
- Dashboard recommendations: chart distribution, track retry loops, and alert on sustained growth in `failed`/`retrying` buckets.

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
- Streaming control: `--stream` emits NDJSON pipeline events to stdout while summaries move to stderr, `--no-stream` retains the eager wrapper for scripts that expect full materialisation.
- Batch orchestration: `--batch path.ndjson` (chunked automatically with `--chunk-size`), `--id` for targeted document replays, and `--limit` to cap records.
- Resume & auto pipelines: `--resume`, `--auto`, `--page-size`, `--start-date`, `--end-date`, and `--rate-limit` control long-running fetches.
- Validation toggles: `--strict-validation`, `--skip-validation`, `--fail-fast`, `--dry-run`, and the new `--schema schema.json` guardrail to validate NDJSON rows against JSON Schema when available.
- Logging & UX: `--progress/--no-progress`, `--quiet`, `--verbose`, `--log-level`, `--log-file`, and `--error-log` tailor operator feedback.
- Help output: `med ingest --help` renders an overview, dynamic adapter list, markdown-formatted examples, and links to the reference docs.

### Command Overview & Examples

```bash
# Run a batch ingest with schema validation and resume semantics
med ingest demo --batch params.ndjson --schema schemas/demo.json --resume

# Stream auto-mode results to downstream tooling with JSON output
med ingest umls --auto --limit 1000 --output json --show-timings

# Perform a dry-run validation (no adapter execution) with a specific ID set
med ingest nice --id guideline-123 --id guideline-456 --dry-run --summary-only
```

Running `med ingest --help` lists all adapters discovered in the registry and highlights the most common workflows. The "See also" epilog links directly to this runbook, the command reference, and the documentation archive for historical context.

## Batch & Auto Modes

- The CLI (`med ingest`) supports `--auto` to stream ingested `doc_id`s and advance the ledger to `LedgerState.COMPLETED`.
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

### Pipeline event stream

- `IngestionPipeline.stream_events()` emits typed `PipelineEvent` objects that describe document lifecycle milestones,
  adapter state transitions, failures, and progress snapshots.
- Event types include:
  - `DocumentStarted` / `DocumentCompleted` / `DocumentFailed` for per-document lifecycle tracking
  - `BatchProgress` for aggregated counts, ETA estimation, queue depth, and backpressure statistics
  - `AdapterStateChange` whenever an adapter transitions between initialising, invocation, completion, or failure states
- Supply `event_filter` or `event_transformer` callbacks to declaratively tailor which events reach the consumer (for example
  only failures) or to enrich payloads before downstream fan-out.
- The event queue is bounded (`buffer_size`, default 100) to provide backpressure; when consumers are slower than the producer,
  `BatchProgress` carries `backpressure_wait_seconds`/`backpressure_wait_count` so you can alert on the build-up.
- Example patterns:
  - `event_filter=errors_only` to forward only `DocumentFailed` events into incident pipelines
- `event_transformer=lambda event: enrich(event)` to attach SLA metadata before publishing to SSE or WebSocket clients

### Streaming architecture overview

- `IngestionPipeline.stream_events()` is the authoritative execution surface. All other helpers (`iter_results()`, `run_async()`) consume this stream so progress, backpressure, and failure data stay consistent.
- Event queue backpressure is enforced via the `buffer_size` argument (default 100). When the consumer lags, the queue depth saturates and the adapter automatically pauses until space becomes available.
- `BatchProgress` events now include `checkpoint_doc_ids` and an `is_checkpoint` flag, allowing orchestrators to persist progress atomically without replaying the entire stream.
- Adapter authors can raise structured signals using `BaseAdapter.emit_event()`. The HTTP base adapter automatically emits `AdapterRetry` whenever the underlying client retries a request, exposing status codes and attempt counts.
- Structured logging captures every emitted event at DEBUG level with JSON payloads so operators can replay executions by tailing the ingestion service logs.

#### Event catalogue

| Event | Description |
| --- | --- |
| `DocumentStarted` | Document handed to the adapter for parse/validate; includes adapter name and invocation parameters. |
| `DocumentCompleted` | Successful parse/validate/write; payload contains the serialised `Document` and adapter metadata. |
| `DocumentFailed` | Terminal failure; captures retry metadata (`retry_count`, `is_retryable`) and the exception type. |
| `AdapterRetry` | HTTP transport issued a retry (status codes 429/502/503/504); exposes attempt number and upstream status. |
| `BatchProgress` | Periodic heartbeat; now carries queue depth, ETA, backpressure metrics, and checkpoint doc IDs. |
| `AdapterStateChange` | Lifecycle transitions for adapter startup, invocation boundaries, completion, or failure. |

### Checkpointing recipes

- Configure `checkpoint_interval` to the cadence that downstream storage can persist (e.g., 1,000 documents for S3 checkpoints). Each checkpoint event includes `checkpoint_doc_ids` so you can durably record the most recent batch.
- Supply `completed_ids` when restarting a run to skip already-processed documents; the pipeline filters these before emitting `DocumentStarted`, preserving idempotence.
- Combine checkpoint metadata with ledger snapshots for full recovery: store `checkpoint_doc_ids`, ledger offsets, and the `BatchProgress.timestamp` value to resume precisely where the previous run paused.

#### Adapter template snippet

```python
class ExampleAdapter(HttpAdapter[JSONMapping]):
    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[JSONMapping]:
        for page in self._pages:
            try:
                yield await self._fetch_page(page)
            except HTTPError as exc:
                self.emit_event(
                    AdapterRetry(
                        timestamp=time.time(),
                        pipeline_id="",
                        adapter=self.source,
                        attempt=getattr(exc, "request", {}).get("attempt", 1),
                        error=str(exc),
                        status_code=getattr(exc.response, "status_code", None),
                    )
                )
                raise
```

Include `self.emit_event` calls at meaningful checkpoints (long-running fetch loops, retries, schema warnings) so downstream consumers receive the same visibility as first-party adapters.

### Backpressure tuning

- Monitor `BatchProgress.queue_depth` and `BatchProgress.buffer_size` to detect when consumers fall behind. Sustained ratios near 1 indicate downstream bottlenecks.
- Alert on `backpressure_wait_seconds` and `backpressure_wait_count`. Rising values mean the producer is frequently pausing; consider increasing `buffer_size` or scaling consumers.
- New Prometheus metrics (`ingest_pipeline_events_total`, `ingest_pipeline_queue_depth`, `ingest_pipeline_checkpoint_latency_seconds`, `ingest_pipeline_duration_seconds`, `ingest_pipeline_consumption_total`) expose event mix, queue health, checkpoint latencies, run-time distribution, and how far teams have migrated off eager wrappers.

### Streaming API endpoint

- `POST /api/ingestion/stream` returns Server-Sent Events (SSE) with the same event payloads produced by `stream_events()`. Each SSE message includes the event type in the `event:` field and the JSON body in `data:`.
- Request body mirrors CLI options: `adapter`, optional `params` array, `resume`, `buffer_size`, `progress_interval`, `checkpoint_interval`, `completed_ids`, and `total_estimated`.
- SSE responses set `Cache-Control: no-cache` and `X-Accel-Buffering: no` so intermediaries forward events immediately. Client disconnects are detected via `Request.is_disconnected()` to stop work promptly.
- Rate limiting shares the same fixed-window policy as other APIs and returns `X-RateLimit-*` headers on the SSE response.

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

## HTTP Client Telemetry

`AsyncHttpClient` exposes structured telemetry so operators can observe the full request lifecycle without wrapping adapters in bespoke logging or metric code.

### Event Types

Each lifecycle hook receives a dataclass instance with contextual metadata:

| Event | Dataclass | Key fields |
|-------|-----------|------------|
| Request started | `HttpRequestEvent` | `request_id`, `url`, `method`, sanitized `headers` |
| Response received | `HttpResponseEvent` | `status_code`, `duration_seconds`, `response_size_bytes` |
| Retry scheduled | `HttpRetryEvent` | `attempt`, `delay_seconds`, `reason`, `will_retry` |
| Limiter backoff | `HttpBackoffEvent` | `wait_time_seconds`, `queue_depth`, `queue_saturation` |
| Error surfaced | `HttpErrorEvent` | `error_type`, `message`, `retryable` |

Events share a `request_id`, allowing downstream systems to correlate retries, backoff, and completion.

### Callback Interface

Callbacks can be passed directly to `AsyncHttpClient` or registered later:

```python
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.telemetry import HttpRequestEvent

def log_request(event: HttpRequestEvent) -> None:
    LOG.info("HTTP %s %s", event.method, event.url, extra={"request_id": event.request_id})

client = AsyncHttpClient(on_request=log_request)

# Register more callbacks after construction (per-host mappings supported)
client.add_telemetry({
    "api.example.com": logging_telemetry,
    "ratelimited.partner": prometheus_helper,
})
```

### Built-in Telemetry Helpers

* `LoggingTelemetry` – emits structured log records with the full event payload (sensitive headers redacted).
* `PrometheusTelemetry` – exports counters/histograms/gauges when `prometheus_client` is installed; disabled automatically otherwise.
* `TracingTelemetry` – creates OpenTelemetry spans (pass a tracer to opt in; no-op if OpenTelemetry is absent).
* `CompositeTelemetry` – fan-out helper that executes multiple telemetry handlers while isolating failures.

These helpers can be combined via the `telemetry` constructor argument or `client.add_telemetry`.

### Prometheus Metrics

`PrometheusTelemetry` records the following metrics (all with a `host` label):

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total{method,host,status}` | Counter | Successful + failed requests (status is HTTP code or exception type) |
| `http_request_duration_seconds{method,host}` | Histogram | Request latency distribution |
| `http_response_size_bytes{method,host}` | Histogram | Response payload sizes |
| `http_retries_total{host,reason}` | Counter | Retry attempts grouped by reason |
| `http_backoff_duration_seconds{host}` | Histogram | Limiter-enforced wait times |
| `http_limiter_queue_depth{host}` | Gauge | Current limiter queue depth |
| `http_limiter_queue_saturation{host}` | Gauge | Queue depth as % of capacity |

A ready-to-import Grafana dashboard (`ops/monitoring/grafana/http-client-telemetry.json`) visualises request volume, latency percentiles, retries, and limiter saturation.

### Per-Host Telemetry Patterns

Adapters that talk to multiple APIs can scope telemetry by host:

```python
from Medical_KG.ingestion.telemetry import LoggingTelemetry, PrometheusTelemetry

telemetry_by_host = {
    "api.hipaa.local": LoggingTelemetry(level=logging.WARNING),
    "partner-rate-limited.com": [PrometheusTelemetry()],
}

adapter = PubMedAdapter(context, client, telemetry=telemetry_by_host)
```

The base `HttpAdapter` automatically forwards telemetry definitions to the shared client, so adapter constructors only need to expose a `telemetry` keyword when they want custom defaults.

### Operational Examples

- **Structured request logging** (task 13.1):

  ```python
  logging_telemetry = LoggingTelemetry(logger=logging.getLogger("ingest.http"))
  client = AsyncHttpClient(telemetry=[logging_telemetry])
  ```

- **Rate-limit budget tracking** (task 13.2): use `http_limiter_queue_depth` + `http_limiter_queue_saturation` in Grafana to watch headroom per host. The new dashboard includes saturation gauges with alert thresholds.

- **Retry alerting** (task 13.3): alert on `sum(rate(http_retries_total[5m])) by (reason)` exceeding expected baselines to catch upstream instability before failures cascade.

- **Adapter-specific telemetry** (task 13.4): pass telemetry into the adapter constructor (`PubMedAdapter(..., telemetry=LoggingTelemetry())`) to scope handlers to that integration while sharing the client across sources.

- **OpenTelemetry tracing** (task 13.5): instantiate `TracingTelemetry(tracer=trace.get_tracer("ingest.http"))` and pass it to the client to produce spans with retry/backoff events annotated.

### Performance Considerations

Telemetry callbacks execute synchronously after each lifecycle event. Keep handlers lightweight (logging, metric increments, span annotations) to maintain the observed <5% overhead during synthetic load tests. Expensive work should be deferred to background tasks.

### Troubleshooting

- Missing metrics usually indicate `prometheus_client` is not installed; set `enable_metrics=False` to silence the warning and rely on logging/trace callbacks.
- Spikes in `http_limiter_queue_saturation` above 0.8 trigger a warning log and indicate the limiter is the bottleneck—either lower concurrency or request higher upstream quotas.
- If callbacks raise exceptions they are logged at `WARNING` level and suppressed; check application logs for `"Telemetry callback"` messages when instrumentation appears inactive.
