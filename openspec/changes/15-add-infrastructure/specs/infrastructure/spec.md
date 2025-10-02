# Infrastructure Capability

## ADDED Requirements

### Requirement: Kubernetes Deployments

The system SHALL deploy all services as K8s Deployments with HPAs, PDBs, and resource limits.

#### Scenario: Create Deployments

- **WHEN** deploying services
- **THEN** the system SHALL create Deployments for api, ingest, parser, chunker, splade, qwen-embed-vllm, indexer, extract, eval, catalog with replicas, resource requests/limits

#### Scenario: GPU node affinity

- **WHEN** deploying GPU workloads (mineru, vllm, splade)
- **THEN** Pods SHALL have nodeSelector{gpu: "true"} and tolerations for GPU taints

#### Scenario: Horizontal Pod Autoscalers

- **WHEN** load increases
- **THEN** HPAs SHALL scale Deployments based on CPU/GPU/RPS metrics (min/max replicas configured)

#### Scenario: Pod Disruption Budgets

- **WHEN** nodes drain for maintenance
- **THEN** PDBs SHALL ensure minAvailable replicas for high-availability services (api, retrieval)

### Requirement: Helm Charts

The system SHALL provide Helm charts with values-dev.yaml, values-staging.yaml, values-prod.yaml.

#### Scenario: Helm chart structure

- **WHEN** packaging for deployment
- **THEN** Chart SHALL include Chart.yaml, templates/, values.yaml, values-{env}.yaml

#### Scenario: Templating

- **WHEN** rendering manifests
- **THEN** Helm SHALL template K8s resources with env-specific values (image tags, replicas, resources)

#### Scenario: Pre-install hooks

- **WHEN** helm install executes
- **THEN** Hooks SHALL run DB migrations, index creation before main workloads

### Requirement: Data Store Deployments

The system SHALL deploy OpenSearch, Neo4j, Kafka, and Redis with persistence and backups.

#### Scenario: OpenSearch cluster

- **WHEN** deploying search
- **THEN** the system SHALL deploy 3-node OpenSearch cluster (data + ingest nodes) with persistent volumes and snapshot repository

#### Scenario: Neo4j cluster

- **WHEN** deploying graph
- **THEN** the system SHALL deploy Neo4j with 1 core + 2 read replicas, APOC + n10s plugins, backup schedule

#### Scenario: Kafka cluster

- **WHEN** event streaming enabled
- **THEN** the system SHALL deploy 3-broker Kafka cluster with ZooKeeper or KRaft mode

#### Scenario: Redis cache

- **WHEN** deploying cache
- **THEN** the system SHALL deploy Redis (1 master + 2 replicas, persistence disabled for cache use)

### Requirement: Orchestration DAGs

The system SHALL define Prefect/Airflow DAGs for auto_flow_nonpdf, pdf_flow, and catalog_refresh_flow.

#### Scenario: Auto flow DAG

- **WHEN** defining auto_flow_nonpdf
- **THEN** DAG SHALL include tasks: ingest → parse → IR → chunk → facet → embed → index → extract/map → KG

#### Scenario: PDF flow DAG

- **WHEN** defining pdf_flow
- **THEN** DAG SHALL include: ingest_pdf → STOP (manual MinerU trigger) → mineru_run → IR → STOP (manual postpdf-start) → chunk → ...

#### Scenario: GPU guards in DAGs

- **WHEN** GPU-dependent task executes
- **THEN** DAG SHALL check GPU availability and fail if unavailable (no CPU fallback)

### Requirement: Monitoring Stack

The system SHALL deploy Prometheus for metrics scraping and Grafana for dashboards.

#### Scenario: Prometheus deployment

- **WHEN** deploying monitoring
- **THEN** the system SHALL deploy Prometheus server with scrape_interval=10s, retention=30d, and service monitors for all services

#### Scenario: Recording rules

- **WHEN** computing aggregates
- **THEN** Prometheus SHALL define recording rules for P50/P95/P99 latency, error_rate, throughput

#### Scenario: Alerting rules

- **WHEN** defining alerts
- **THEN** Prometheus SHALL configure: P95 > SLO → page, service down → page, EL acceptance < 0.6 → warn

### Requirement: Grafana Dashboards

The system SHALL provide pre-configured Grafana dashboards for retrieval, GPU, ingestion, extraction, KG, and APIs.

#### Scenario: Retrieval dashboard

- **WHEN** viewing retrieval metrics
- **THEN** dashboard SHALL show latency histograms, component score distributions, nDCG trends

#### Scenario: GPU dashboard

- **WHEN** monitoring GPUs
- **THEN** dashboard SHALL show utilization %, memory used, throughput for vLLM/SPLADE/MinerU

#### Scenario: Ingestion dashboard

- **WHEN** tracking ingestion
- **THEN** dashboard SHALL show docs/sec per source, success/failure rates, ledger state distribution

### Requirement: Alerting Integration

The system SHALL integrate with PagerDuty/Opsgenie for critical alerts.

#### Scenario: Alert routing

- **WHEN** Prometheus alert fires
- **THEN** the system SHALL send to PagerDuty/Opsgenie via webhook

#### Scenario: Severity mapping

- **WHEN** defining alerts
- **THEN** P1 (service down) → page immediately, P2 (SLO breach) → page if not ack'd in 15min, P3 (warning) → Slack only

#### Scenario: Runbook links

- **WHEN** alert triggers
- **THEN** alert SHALL include runbook URL for mitigation steps

### Requirement: Terraform Infrastructure-as-Code

The system SHALL define Terraform modules for VPC, EKS/GKE, OpenSearch, Neo4j, S3/GCS, Kafka.

#### Scenario: VPC module

- **WHEN** provisioning network
- **THEN** Terraform SHALL create VPC with public/private subnets, NAT gateway, security groups

#### Scenario: EKS module

- **WHEN** provisioning K8s
- **THEN** Terraform SHALL create EKS cluster with node groups (CPU nodes, GPU nodes with A100/H100)

#### Scenario: OpenSearch module

- **WHEN** provisioning search
- **THEN** Terraform SHALL create OpenSearch domain with encryption, snapshots, access policies

### Requirement: CI/CD Pipeline

The system SHALL automate lint, test, build, deploy via GitHub Actions with staging and prod environments.

#### Scenario: PR checks

- **WHEN** pull request opened
- **THEN** CI SHALL run: ruff check, black --check, mypy, pytest, openapi validation

#### Scenario: Build and push images

- **WHEN** PR merged to main
- **THEN** CI SHALL build Docker images, tag with SHA, push to container registry

#### Scenario: Deploy to staging

- **WHEN** images pushed
- **THEN** CI SHALL helm upgrade staging, run smoke tests, report status

#### Scenario: Deploy to prod

- **WHEN** manual approval granted
- **THEN** CI SHALL helm upgrade prod with canary rollout, run health checks

### Requirement: Backups and Disaster Recovery

The system SHALL implement daily backups for OpenSearch, Neo4j, and object stores with RPO ≤24h, RTO ≤8h.

#### Scenario: OpenSearch snapshots

- **WHEN** backup schedule triggers (03:00 UTC daily)
- **THEN** the system SHALL create OpenSearch snapshot to S3 repository, retain 30 days

#### Scenario: Neo4j backups

- **WHEN** backup schedule triggers (04:00 UTC daily)
- **THEN** the system SHALL execute neo4j-admin dump, upload to S3, retain 30 days, keep PITR logs 7d

#### Scenario: Test restore quarterly

- **WHEN** DR drill executes
- **THEN** the system SHALL restore from backup to test environment and verify data integrity

### Requirement: Observability with OpenTelemetry

The system SHALL collect traces via OpenTelemetry and export to Jaeger/Tempo.

#### Scenario: OTel collector

- **WHEN** deploying observability
- **THEN** the system SHALL deploy OTel collector to receive traces from all services

#### Scenario: Trace sampling

- **WHEN** configuring tracing
- **THEN** sampling rate SHALL be 0.1 in prod, 1.0 in dev

#### Scenario: Instrument service calls

- **WHEN** services make requests
- **THEN** OpenSearch, Neo4j, vLLM calls SHALL be instrumented with spans

### Requirement: Security and Networking

The system SHALL enforce private subnets for data stores, WAF for API, and service-to-service mTLS.

#### Scenario: Private subnets

- **WHEN** deploying data stores
- **THEN** OpenSearch, Neo4j, Kafka, Redis SHALL be in private subnets with no public IPs

#### Scenario: API behind WAF

- **WHEN** exposing API
- **THEN** API SHALL be behind ALB/NLB with WAF (rate limiting, IP allowlists)

#### Scenario: Optional mTLS

- **WHEN** service mesh enabled (Istio/Linkerd)
- **THEN** service-to-service traffic SHALL use mTLS
