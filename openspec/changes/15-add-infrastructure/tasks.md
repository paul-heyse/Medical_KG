# Implementation Tasks

## 1. Kubernetes Manifests

- [x] 1.1 Create Deployments (api, ingest, parser, chunker, splade, qwen-embed-vllm, indexer, extract, eval, catalog)
- [x] 1.2 Create Services (ClusterIP for internal; LoadBalancer/NodePort for API)
- [x] 1.3 Create ConfigMaps (config.yaml, policy.yaml per environment)
- [x] 1.4 Create Secrets (API keys, DB credentials via Vault or K8s secrets)
- [x] 1.5 Create HPAs (horizontal pod autoscalers on CPU/GPU/RPS)
- [x] 1.6 Create PDBs (pod disruption budgets for high-availability services)
- [x] 1.7 Create Ingress (ALB/NLB with WAF; TLS termination)
- [x] 1.8 Create ServiceAccounts + RBAC (least privilege per service)

## 2. GPU Node Configuration

- [x] 2.1 Label GPU nodes (gpu=true, gpu_type=a100|h100|a10g)
- [x] 2.2 Add taints/tolerations for GPU workloads (mineru-gpu, vllm-gpu, splade-gpu)
- [x] 2.3 Configure resource requests/limits (memory, GPU count)
- [x] 2.4 Add node affinity (prefer high-memory nodes for embeddings)

## 3. Helm Charts

- [x] 3.1 Create Chart.yaml (version, dependencies)
- [x] 3.2 Create values.yaml (defaults)
- [x] 3.3 Create values-dev.yaml (local/dev overrides)
- [x] 3.4 Create values-staging.yaml (staging overrides)
- [x] 3.5 Create values-prod.yaml (production overrides)
- [x] 3.6 Templatize K8s manifests (use Helm templating for env-specific values)
- [x] 3.7 Add hooks (pre-install, post-upgrade for DB migrations, index rebuilds)

## 4. Data Store Deployments

- [x] 4.1 Deploy OpenSearch/Elasticsearch (3-node cluster; data + ingest nodes; snapshot repository)
- [x] 4.2 Deploy Neo4j (1 core + 2 read replicas; APOC + n10s plugins; backup schedule)
- [x] 4.3 Deploy Kafka (optional; 3-broker cluster for event streaming)
- [x] 4.4 Deploy Redis (caching; 1 master + 2 replicas; persistence disabled)
- [x] 4.5 Configure persistent volumes (EBS/GCE PD; snapshot policies)

## 5. Orchestration DAGs (Prefect/Airflow)

- [x] 5.1 Define auto_flow_nonpdf (ingest → parse → IR → chunk → facet → embed → index → extract/map → KG)
- [x] 5.2 Define pdf_flow (ingest_pdf → STOP → mineru_run → IR → STOP → postpdf_start → chunk → ...)
- [x] 5.3 Define catalog_refresh_flow (download ontologies → parse → normalize → embed → index → write)
- [x] 5.4 Add GPU guards (check GPU availability; fail if unavailable)
- [x] 5.5 Add retry logic (transient failures → exponential backoff)
- [x] 5.6 Add monitoring (emit DAG run metrics; alert on failures)

## 6. Prometheus Monitoring

- [x] 6.1 Deploy Prometheus server (scrape_interval 10s; retention 30d)
- [x] 6.2 Configure service monitors (scrape /metrics from each service)
- [x] 6.3 Define recording rules (P50/P95/P99 latency, error_rate, throughput)
- [x] 6.4 Define alerting rules (P95 > SLO, service down, GPU unavailable, EL acceptance < 0.6)

## 7. Grafana Dashboards

- [x] 7.1 Retrieval dashboard (latency histograms, component scores Venn, nDCG trends)
- [x] 7.2 GPU utilization dashboard (vLLM/SPLADE/MinerU GPU%, memory, throughput)
- [x] 7.3 Ingestion dashboard (docs/sec per source, success/failure rates, ledger states)
- [x] 7.4 Extraction dashboard (PICO completeness, effect F1, AE accuracy over time)
- [x] 7.5 KG dashboard (node/edge counts, write TPS, SHACL violations)
- [x] 7.6 API dashboard (requests/sec, latency P95, error rate, rate limit consumption)

## 8. Alerting

- [x] 8.1 Integrate with PagerDuty/Opsgenie (webhook for critical alerts)
- [x] 8.2 Define alert severity (P1 service down, P2 SLO breach, P3 warning thresholds)
- [x] 8.3 Add runbook links to alerts (point to docs for mitigation)
- [x] 8.4 Configure on-call rotation

## 9. Terraform Modules

- [x] 9.1 VPC module (subnets, NAT gateway, security groups)
- [x] 9.2 EKS/GKE module (K8s cluster, node groups, GPU nodes)
- [x] 9.3 OpenSearch module (domain, snapshots, access policies)
- [x] 9.4 Neo4j module (EC2 instances or managed service, backups)
- [x] 9.5 S3/GCS module (buckets for IR, MinerU artifacts, backups; lifecycle policies)
- [x] 9.6 Kafka module (MSK/Confluent Cloud or self-managed)
- [x] 9.7 Vault module (secrets management; dynamic DB credentials)

## 10. CI/CD Pipeline

- [x] 10.1 Lint (ruff, black, mypy, OpenAPI validation)
- [x] 10.2 Test (pytest unit + integration; eval smoke test)
- [x] 10.3 Build images (Docker build for each service; tag with SHA)
- [x] 10.4 Push images (to ghcr.io or ECR/GCR)
- [x] 10.5 Deploy to staging (Helm upgrade; run smoke tests)
- [x] 10.6 Deploy to prod (manual approval; Helm upgrade; canary rollout)
- [x] 10.7 Post-deploy validation (health checks, smoke queries)

## 11. Observability & Tracing

- [x] 11.1 Deploy OpenTelemetry collector (receive traces from all services)
- [x] 11.2 Configure trace sampling (0.1 in prod; 1.0 in dev)
- [x] 11.3 Export traces to Jaeger/Tempo
- [x] 11.4 Instrument all service calls (OpenSearch, Neo4j, vLLM)

## 12. Security & Networking

- [x] 12.1 Private subnets for data stores (no public IPs)
- [x] 12.2 API behind ALB/NLB + WAF (rate limiting, IP allowlists)
- [x] 12.3 Egress via NAT with allowlists (NLM, FDA, WHO, etc. endpoints only)
- [x] 12.4 Service-to-service mTLS (optional; via service mesh like Istio)
- [x] 12.5 Secrets from Vault (dynamic credentials; 30-day rotation)

## 13. Backups & DR

- [x] 13.1 OpenSearch snapshots (daily at 03:00 UTC; retain 30)
- [x] 13.2 Neo4j backups (daily at 04:00 UTC; retain 30; PITR logs 7d)
- [x] 13.3 S3 versioning enabled (lifecycle move to infrequent access after 90d)
- [x] 13.4 Cross-region replication (optional for DR)
- [x] 13.5 Test restore quarterly (runbook documented)

## 14. Cost Controls

- [x] 14.1 TTL policies for transient topics (7d)
- [x] 14.2 ILM warm/cold tiers in OpenSearch
- [x] 14.3 Spot GPU nodes for non-urgent backfills
- [x] 14.4 Compression (NDJSON gz; Kafka LZ4; API gzip)
- [x] 14.5 Budget alerts (AWS Cost Anomaly Detection)

## 15. Testing

- [x] 15.1 Terraform plan (validate all modules)
- [x] 15.2 Helm dry-run (validate templates)
- [x] 15.3 Deploy to dev cluster (E2E smoke test)
- [x] 15.4 Chaos testing (kill pods, drop network, fill disk)

## 16. Documentation

- [x] 16.1 Deployment guide (prerequisites, Terraform apply, Helm install)
- [x] 16.2 Runbooks (scale up/down, GPU node failures, index rebuild, catalog refresh)
- [x] 16.3 DR procedure (restore from backups, failover regions)
- [x] 16.4 Cost optimization guide
