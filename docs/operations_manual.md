# Operations Manual

Central index for Medical KG runbooks, contacts, and cadences.

## Contact Tree

- **Primary On-Call** – PagerDuty schedule `medical-kg-primary`.
- **Secondary On-Call** – PagerDuty schedule `medical-kg-secondary` (escalate after 15 min).
- **Engineering Manager** – <eng-manager@medkg.example.com>.
- **Operations Lead** – <ops-lead@medkg.example.com>.
- **Clinical Liaison** – <clinical@medkg.example.com>.
- **Security Officer** – <security@medkg.example.com>.

## Runbook Index

| Scenario                           | Runbook                                      |
|-----------------------------------|-----------------------------------------------|
| Hot configuration reload          | `ops/runbooks/01-hot-config-change.md`       |
| Retrieval scaling (HPA/KEDA)      | `ops/runbooks/02-scale-retrieval.md`         |
| Index rebuild / alias flip        | `ops/runbooks/03-index-rebuild.md`           |
| GPU / vLLM failure recovery       | `ops/runbooks/04-gpu-node-failure.md`        |
| Incident response & comms         | `ops/runbooks/05-incident-response.md`       |
| Catalog refresh / license checks  | `ops/runbooks/06-catalog-refresh.md`         |
| Unified ingestion CLI operations  | `docs/ingestion_runbooks.md`                 |
| Ledger state machine & compaction | `docs/ingestion_runbooks.md#ledger-state-machine` |
| Datastore failover (Neo4j/OS)     | `ops/runbooks/07-datastore-failover.md`      |
| Briefing generation gaps          | `ops/runbooks/08-briefing-troubleshooting.md` |
| Unified ingestion CLI operations  | `docs/ingestion_cli_reference.md`            |
| CLI migration history             | `docs/archive/README.md#cli-unification`     |
| Optional dependency diagnostics   | `docs/dependencies.md`                       |

## Escalation Matrix

| Severity | Response Time | Actions                                             |
|----------|---------------|-----------------------------------------------------|
| P1       | Immediate     | Page primary, engage secondary, status page update |
| P2       | <15 minutes   | Page primary, inform product, assess impact        |
| P3       | <1 hour       | Triage in business hours, track in ops board       |
| P4       | Next day      | Planned maintenance / documentation updates        |

## Communication Channels

- **Slack** – `#ops`, `#incidents`, `#medical-kg`.
- **Status Page** – <https://status.medkg.example.com>.
- **Email** – <ops@medkg.example.com> for scheduled maintenance notices.

## Ingestion Metrics & Logs

- **Counters** – `ingest_pipeline_events_total{event_type,adapter}` tracks emitted pipeline events. Sudden spikes in `DocumentFailed` or `AdapterRetry` should trigger incident review.
- **Adoption tracking** – `ingest_pipeline_consumption_total{mode,adapter}` surfaces how frequently teams rely on streaming (`mode="stream_events"`) versus eager wrappers (`mode="run_async"`). Investigate services that remain on eager paths after the migration freeze.
- **Histograms** – `ingest_pipeline_duration_seconds` captures total run time distribution; `ingest_pipeline_checkpoint_latency_seconds` measures time between checkpoint-ready `BatchProgress` events.
- **Gauges** – `ingest_pipeline_queue_depth{adapter}` exposes current backpressure; alert when depth approaches `buffer_size` for >5 minutes.
- **Structured logging** – every event is logged at DEBUG with JSON via the `pipeline_event` message. Forward to the log aggregator so SSE consumers can be replayed during incidents.
- **SSE Endpoint** – `/api/ingestion/stream` delivers the same events to external consumers. Ensure Grafana dashboards consume both Prometheus metrics and SSE streams for end-to-end visibility.

## Cadences

- Daily stand-up (Operations) – 09:00 UTC, review overnight alerts.
- Weekly ops sync – review metrics, open incidents, cost trends.
- Monthly release review – confirm roadmap, debrief major changes.
- Quarterly DR drill – execute `ops/release/pipeline.md` on staging + restore from backup.

Refer to `docs/continuous_improvement.md` for KPIs and retrospection process.

## Ledger Health Dashboards

- **Prometheus metrics** – scrape `med_ledger_documents_by_state`, `med_ledger_state_transitions_total`, `med_ledger_state_duration_seconds`, and `med_ledger_errors_total` to populate the "Ledger Overview" Grafana dashboard. Alert when `failed` or `retrying` states exceed 5% of active documents for 10 minutes.
- **Snapshot freshness** – schedule `med ledger compact --ledger-path <path>` nightly and ensure snapshots appear in `ledger.snapshots`. If a snapshot is older than 36h, raise a P2 incident and rebuild from the JSONL delta log.
- **Stuck document checks** – run `med ledger stuck --hours 6` during daily ops review; investigate any entries with metadata indicating adapter errors or missing artifacts.
- **Runbook** – `ops/runbooks/09-ledger-maintenance.md` covers the enum-only audit, compaction, dashboards, and communication templates introduced after removing `LedgerState.LEGACY`.

## Briefing Exports

- See `docs/briefing.md` for formatter defaults and handling of partial payloads.
- Escalate persistent placeholder values using `ops/runbooks/08-briefing-troubleshooting.md`.
