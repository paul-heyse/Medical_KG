# Deployment Operations Capability

## ADDED Requirements

### Requirement: Operational Runbooks

The system SHALL provide comprehensive runbooks for hot config changes, scale operations, index rebuilds, catalog refresh, GPU failures, and incident response.

#### Scenario: Hot config change runbook

- **WHEN** operator needs to change retrieval weights
- **THEN** runbook SHALL document: POST /admin/reload, verify /version shows new config_version, check metrics

#### Scenario: Scale retrieval runbook

- **WHEN** load increases
- **THEN** runbook SHALL document: HPA on CPU for I/O bound, RPS autoscaler via KEDA for request bound

#### Scenario: Index rebuild runbook

- **WHEN** OpenSearch schema changes
- **THEN** runbook SHALL document: create chunks_v2, dual-write, verify Recall@20 delta <2%, flip alias, drop old index

#### Scenario: GPU node failure runbook

- **WHEN** GPU node fails
- **THEN** runbook SHALL document: cordon node, drain pods, replace/repair node, uncordon, verify GPU visibility

### Requirement: E2E Verification Suite

The system SHALL provide automated E2E test verifying full pipeline from ingest to briefing output.

#### Scenario: Ingest documents

- **WHEN** E2E test runs
- **THEN** the test SHALL ingest 10 PMC OA + 10 SPL + 10 NCT via full auto pipeline

#### Scenario: Verify all processing steps

- **WHEN** documents ingested
- **THEN** the test SHALL verify: chunk, facet, embed, index, retrieve (run 50 gold queries), EL (100 mentions), extract (PICO/effects/AEs), KG write (SHACL pass)

#### Scenario: Generate briefing

- **WHEN** processing complete
- **THEN** the test SHALL generate sample dossier and verify: all sections present, 100% citation coverage

#### Scenario: E2E latency check

- **WHEN** measuring performance
- **THEN** E2E SHALL complete ingest → briefing in <5 min for 10 docs

### Requirement: Performance Tuning Guides

The system SHALL document tuning for retrieval weights, OpenSearch shards, Neo4j memory, and GPU batching.

#### Scenario: Retrieval weight tuning

- **WHEN** SPLADE service degrades
- **THEN** guide SHALL document: reweight to dense=0.7, bm25=0.3, monitor component_contribution_pct metric

#### Scenario: OpenSearch tuning

- **WHEN** optimizing search
- **THEN** guide SHALL document: shard size 20-40 GB, refresh_interval 30s, indexing buffer 10% heap

#### Scenario: Neo4j tuning

- **WHEN** optimizing graph queries
- **THEN** guide SHALL document: batch upserts 1000 nodes/edges/tx, dbms.memory.pagecache to dataset working set

#### Scenario: GPU batch tuning

- **WHEN** optimizing embeddings
- **THEN** guide SHALL document: target ≥2.5K tokens/s/GPU for Qwen, adjust batch size dynamically

### Requirement: Load Testing Suite

The system SHALL provide load tests for burst (50 QPS), steady (10 QPS), and mixed intents.

#### Scenario: Burst load test

- **WHEN** running burst test
- **THEN** the system SHALL send 50 QPS for 2 min and measure P95 latency for /retrieve, /extract

#### Scenario: Steady load test

- **WHEN** running steady test
- **THEN** the system SHALL send 10 QPS for 1 hour and verify no memory leaks or degradation

#### Scenario: Mixed intents

- **WHEN** load testing
- **THEN** requests SHALL include: endpoint 40%, AE 25%, dose 15%, eligibility 10%, others 10%

#### Scenario: Back-pressure handling

- **WHEN** P95 > SLO
- **THEN** the system SHALL disable reranker, reduce topK, switch to RRF

### Requirement: Chaos Testing

The system SHALL verify resilience via chaos tests (kill pods, drop network, fill disk, GPU OOM).

#### Scenario: Kill API pod

- **WHEN** chaos test kills API pod
- **THEN** HPA SHALL scale up, requests SHALL re-route, no downtime observed

#### Scenario: Drop network to OpenSearch

- **WHEN** chaos test blocks OpenSearch network
- **THEN** retrieval SHALL return 503, clients SHALL retry

#### Scenario: Fill Neo4j disk

- **WHEN** chaos test fills disk
- **THEN** writes SHALL fail, alerts SHALL trigger, ops SHALL add capacity

#### Scenario: GPU OOM

- **WHEN** batch causes GPU OOM
- **THEN** job SHALL fail with clear error, no corrupt state persisted

### Requirement: Observability Stack

The system SHALL provide Prometheus metrics, Grafana dashboards, OpenTelemetry traces, and structured logs.

#### Scenario: Prometheus metrics

- **WHEN** monitoring services
- **THEN** the system SHALL expose: http_requests_total, retrieve_latency_ms_bucket, fusion_component_score, el_accept_rate, extraction_span_grounding_failures, config_version

#### Scenario: Grafana dashboards

- **WHEN** viewing dashboards
- **THEN** Grafana SHALL show: retrieval latency, GPU utilization, ingestion throughput, extraction quality, KG write TPS, API latency

#### Scenario: OpenTelemetry tracing

- **WHEN** tracing requests
- **THEN** traces SHALL propagate traceparent, instrument OS/Neo4j/vLLM calls, sample at 0.1 in prod

#### Scenario: Structured logs

- **WHEN** logging
- **THEN** logs SHALL be JSON with {level, message, x-request-id, trace_id, user/service, context}

### Requirement: Incident Response Playbook

The system SHALL define severity levels, escalation paths, on-call rotation, and post-mortem template.

#### Scenario: Severity definitions

- **WHEN** incident occurs
- **THEN** severity SHALL be: P1 service down, P2 SLO breach, P3 warning thresholds, P4 maintenance

#### Scenario: Escalation paths

- **WHEN** alert fires
- **THEN** P1 SHALL page immediately, P2 SHALL page if not ack'd in 15min, P3 SHALL Slack alert only

#### Scenario: On-call rotation

- **WHEN** managing on-call
- **THEN** rotation SHALL include primary + secondary, weekly rotation schedule

#### Scenario: Post-mortem template

- **WHEN** incident resolves
- **THEN** post-mortem SHALL include: what happened, timeline, root cause, action items, prevention

### Requirement: Release Checklist

The system SHALL enforce sign-off checklist before production deployment.

#### Scenario: Metrics thresholds

- **WHEN** preparing release
- **THEN** ALL metrics MUST meet targets: Chunking boundary alignment ≥65%, Retrieval Recall@20 per family ≥targets, nDCG@10 ≥baseline+5, EL ID accuracy ≥0.90, EL concepts ≥0.85, Extraction effects F1 ≥0.80, AE mapping ≥0.80, Faithfulness 100%, SHACL 0 violations, Latency P95 within SLOs

#### Scenario: No CPU fallback events

- **WHEN** verifying release
- **THEN** logs SHALL show 0 GPU enforcement failures (no CPU fallback)

#### Scenario: Licenses validated

- **WHEN** preparing release
- **THEN** SNOMED/UMLS/MedDRA licensing SHALL match policy.yaml

#### Scenario: Provenance coverage

- **WHEN** checking KG
- **THEN** ALL :Evidence/:EvidenceVariable/:EligibilityConstraint SHALL have :WAS_GENERATED_BY edge (100% coverage)

#### Scenario: SHACL pass-rate

- **WHEN** validating KG writes
- **THEN** SHACL validation SHALL pass ≥0.98 (units, IDs, code presence, ranges)

#### Scenario: Backups verified

- **WHEN** preparing release
- **THEN** Neo4j, OpenSearch, object store backups SHALL be tested and verified

#### Scenario: Rollback plan tested

- **WHEN** releasing
- **THEN** rollback procedure SHALL be tested in staging

#### Scenario: Sign-off required

- **WHEN** deploying to prod
- **THEN** domain lead, engineering lead, ops lead SHALL all sign-off

### Requirement: Operational Metrics Dashboards

The system SHALL provide dashboards for pipeline throughput, indexing lag, GPU utilization, error rates, and user-facing latency.

#### Scenario: Pipeline throughput

- **WHEN** monitoring pipeline
- **THEN** dashboard SHALL show: docs ingested/hour, chunks created/hour, embeddings computed/hour

#### Scenario: Indexing lag

- **WHEN** monitoring indexing
- **THEN** dashboard SHALL show: time from chunk creation to indexed (target <10 min for non-PDF auto path)

#### Scenario: GPU utilization

- **WHEN** monitoring GPUs
- **THEN** dashboard SHALL show: vLLM, SPLADE, MinerU utilization % (target 80-90% under load)

#### Scenario: Error rates

- **WHEN** monitoring failures
- **THEN** dashboard SHALL show: ingest failures, chunk failures, embed failures, extract failures per type

#### Scenario: User-facing latency

- **WHEN** monitoring performance
- **THEN** dashboard SHALL show: P50/P95/P99 for /retrieve, /extract, /briefing

### Requirement: Continuous Improvement

The system SHALL conduct weekly metrics reviews, monthly quality reviews, quarterly DR drills, and quarterly security reviews.

#### Scenario: Weekly metrics review

- **WHEN** week ends
- **THEN** ops + eng SHALL review: trends, regressions, optimization opportunities

#### Scenario: Monthly quality review

- **WHEN** month ends
- **THEN** domain lead + eng SHALL review: extraction samples, update gold sets

#### Scenario: Quarterly DR drill

- **WHEN** quarter ends
- **THEN** team SHALL restore from backups and verify RTO/RPO targets

#### Scenario: Quarterly security review

- **WHEN** quarter ends
- **THEN** security team SHALL: scan vulnerabilities, review penetration test results, audit logs
