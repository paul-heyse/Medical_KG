# Add Infrastructure (K8s, Orchestration, Monitoring)

## Why

Production deployment requires container orchestration (K8s), workflow orchestration (Prefect/Airflow), monitoring (Prometheus/Grafana), and infrastructure-as-code (Terraform/Helm). Comprehensive infrastructure ensures scalability, reliability, observability, and disaster recovery.

## What Changes

- Create K8s manifests: Deployments (api, ingest, parser, chunker, splade, qwen-embed, indexer, extract, eval, catalog), Services, ConfigMaps, Secrets, HPAs, PDBs, Ingress
- Implement Helm charts (values-dev.yaml, values-staging.yaml, values-prod.yaml)
- Define orchestration DAGs (Prefect/Airflow): auto_flow_nonpdf, pdf_flow (manual gates), catalog_refresh_flow
- Deploy data stores: OpenSearch/Elasticsearch cluster, Neo4j cluster (core + read replicas), Kafka (optional for event streaming), Redis (caching)
- Set up monitoring: Prometheus (metrics scraping), Grafana dashboards (retrieval latency, GPU utilization, ingestion throughput, EL acceptance, extraction quality)
- Add alerting: PagerDuty/Opsgenie integration (P95 latency SLO breaches, service down, GPU unavailable, EL acceptance regression)
- Implement Terraform modules: VPC, EKS/GKE, OpenSearch domain, Neo4j instances, S3 buckets, Kafka cluster
- Add CI/CD pipeline (GitHub Actions): lint, test, build images, deploy to staging, deploy to prod (manual approval)

## Impact

- **Affected specs**: NEW `infrastructure` capability
- **Affected code**: NEW `/infra/k8s/`, `/infra/helm/`, `/infra/terraform/`, `/infra/airflow_dags/`, `.github/workflows/`
- **Dependencies**: Cloud provider (AWS/GCP/Azure), K8s cluster, Helm, Terraform, Prometheus, Grafana
- **Downstream**: All services deployed via K8s; orchestrated via DAGs; monitored via Prometheus/Grafana
