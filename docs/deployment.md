# Deployment Guide

Comprehensive guide for deploying Medical KG to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Configuration](#configuration)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Rollback Procedure](#rollback-procedure)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Tools Required
- **kubectl** (v1.28+)
- **helm** (v3.12+)
- **terraform** (v1.5+) - for infrastructure
- **Python** (3.11+) - for verification scripts
- **AWS CLI** (v2) - if deploying to AWS
- **jq** - for JSON processing

### Access Required
- Kubernetes cluster admin access
- AWS account with appropriate IAM roles (if using AWS)
- Docker registry access (for pulling images)
- Secrets management system (Vault/AWS Secrets Manager)
- Monitoring stack (Prometheus, Grafana)

### Pre-Deployment Checklist
- [ ] All tests passing in CI/CD
- [ ] E2E verification successful in staging
- [ ] Load tests completed successfully
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Runbooks reviewed and up-to-date
- [ ] On-call rotation scheduled
- [ ] Rollback plan documented
- [ ] Stakeholder approval obtained

## Infrastructure Setup

### 1. Provision Infrastructure with Terraform

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan -var-file=prod.tfvars -out=tfplan

# Apply (creates VPC, EKS, OpenSearch, Neo4j, S3, etc.)
terraform apply tfplan
```

**Key Resources Created**:
- VPC with public/private subnets
- EKS cluster (control plane + worker nodes)
- OpenSearch cluster (3 data nodes, 2 master nodes)
- Neo4j cluster (3 core + 2 read replicas)
- S3 buckets (data, snapshots, artifacts)
- GPU node group (for vLLM/embeddings)
- ALB/NLB for API ingress
- RDS for metadata (optional)

### 2. Configure kubectl

```bash
# Get kubeconfig for EKS cluster
aws eks update-kubeconfig --name medkg-prod --region us-east-1

# Verify connectivity
kubectl get nodes

# Expected output: List of nodes including GPU nodes
```

### 3. Install Core Kubernetes Components

```bash
# Install NVIDIA device plugin (for GPU nodes)
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f infra/helm/prometheus-values.yaml

# Install Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx --create-namespace \
  -f infra/helm/ingress-values.yaml

# Install Cert Manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

## Configuration

### 1. Prepare Secrets

```bash
# Create namespace
kubectl create namespace medkg

# Create secrets from Vault/AWS Secrets Manager
kubectl create secret generic medkg-secrets -n medkg \
  --from-literal=jwt-secret=$JWT_SECRET \
  --from-literal=opensearch-password=$OS_PASSWORD \
  --from-literal=neo4j-password=$NEO4J_PASSWORD \
  --from-literal=api-key=$API_KEY

# Create Docker registry secret (if using private registry)
kubectl create secret docker-registry medkg-registry -n medkg \
  --docker-server=registry.example.com \
  --docker-username=$REGISTRY_USER \
  --docker-password=$REGISTRY_PASSWORD
```

### 2. Prepare Configuration Files

```bash
# Copy production config
cp src/Medical_KG/config/config-prod.yaml deployment/config.yaml

# Update with environment-specific values
vim deployment/config.yaml

# Create ConfigMap
kubectl create configmap medkg-config -n medkg \
  --from-file=config.yaml=deployment/config.yaml \
  --from-file=policy.yaml=src/Medical_KG/config/policy.yaml
```

### 3. Prepare Helm Values

```bash
# Edit production values
vim infra/helm/values-prod.yaml

# Key settings to review:
# - Image tags (use specific versions, not :latest)
# - Resource limits (CPU, memory, GPU)
# - Replica counts (start conservative, scale up as needed)
# - Ingress hostnames
# - Monitoring endpoints
```

## Deployment Steps

### 1. Deploy Application

```bash
# Install Medical KG Helm chart
helm install medkg ./infra/helm/medkg \
  -n medkg \
  -f infra/helm/values-prod.yaml \
  --wait \
  --timeout 10m

# Watch deployment
kubectl get pods -n medkg -w
```

### 2. Wait for All Pods Ready

```bash
# Check deployment status
kubectl get deployments -n medkg

# All should show READY replicas equal to DESIRED

# Check pod health
kubectl get pods -n medkg

# All should be Running with READY 1/1
```

### 3. Deploy Monitoring

```bash
# Apply Prometheus alerts
kubectl apply -f ops/monitoring/prometheus-alerts.yaml -n monitoring

# Apply Grafana dashboards
kubectl apply -f ops/monitoring/grafana-dashboards/ -n monitoring

# Verify Prometheus scraping targets
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &
# Open http://localhost:9090/targets - all should be UP
```

### 4. Configure Ingress and TLS

```bash
# Apply ingress rules
kubectl apply -f infra/k8s/ingress-prod.yaml -n medkg

# Verify certificate issued
kubectl get certificate -n medkg
# STATUS should be 'Ready'

# Get ingress IP
kubectl get ingress -n medkg
# Note the ADDRESS (LoadBalancer IP or hostname)
```

### 5. Update DNS

```bash
# Update DNS records to point to ingress
# Example: api.medkg.example.com -> <INGRESS_IP>

# Verify DNS propagation
dig api.medkg.example.com

# Test HTTPS
curl https://api.medkg.example.com/health
```

## Post-Deployment Verification

### 1. Run Health Checks

```bash
# API health
curl https://api.medkg.example.com/health
# Expected: {"status": "ok", "services": {...}}

# Version check
curl https://api.medkg.example.com/version
# Expected: {"api_version": "v1", "component_versions": {...}}

# Verify all components healthy
curl https://api.medkg.example.com/health | jq '.services'
```

### 2. Run E2E Verification

```bash
# Run E2E test suite
python ops/e2e/run_verification.py \
  --env production \
  --base-url https://api.medkg.example.com \
  --api-key $PROD_API_KEY

# Expected: All steps pass
```

### 3. Verify Monitoring

```bash
# Check Prometheus metrics
curl -s 'http://prometheus:9090/api/v1/query?query=up{job="api"}' | jq '.data.result[0].value[1]'
# Expected: "1" (service up)

# Check no active alerts
curl -s 'http://prometheus:9090/api/v1/alerts' | jq '.data.alerts | length'
# Expected: 0 or only info-level alerts
```

- Tail the API pod (`kubectl logs deployment/api -n medkg`) for structured log warnings. New schema validation failures surface as `Configuration invalid` messages with JSON pointers; investigate before proceeding.
- Run `med licensing validate --licenses ops/releases/<date>/licenses.yml` from the release artefact to confirm the hardened loader accepts the payload.
- Review load-test budget output (`python ops/load_test/check_thresholds.py --budget ops/load_test/budget.yaml <report>`) to ensure the shared YAML loader produces structured thresholds.

### 4. Smoke Test Each Endpoint

```bash
# Test retrieval
curl -X POST https://api.medkg.example.com/retrieve \
  -H "Authorization: Bearer $PROD_API_KEY" \
  -d '{"query": "diabetes treatment efficacy", "topK": 5}'

# Test facet generation
curl -X POST https://api.medkg.example.com/facets/generate \
  -H "Authorization: Bearer $PROD_API_KEY" \
  -d '{"chunk_ids": ["<chunk_id>"]}'

# Test extraction
curl -X POST https://api.medkg.example.com/extract/pico \
  -H "Authorization: Bearer $PROD_API_KEY" \
  -d '{"chunk_ids": ["<chunk_id>"]}'
```

### 5. Verify Data Integrity

```bash
# Check Neo4j
kubectl exec -it -n medkg <neo4j-pod> -- cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n) RETURN count(n)"

# Check OpenSearch
curl -u admin:$OS_PASSWORD "https://opensearch:9200/_cat/indices?v"

# Verify expected document counts
```

### 6. Load Test (Optional)

```bash
# Run brief load test
locust -f ops/load_test/locustfile.py \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 5m \
  --host https://api.medkg.example.com \
  --html post_deploy_load_test.html

# Verify P95 latency within SLOs
```

## Rollback Procedure

If issues detected post-deployment:

### Option 1: Helm Rollback (Recommended)

```bash
# List releases
helm history medkg -n medkg

# Rollback to previous release
helm rollback medkg -n medkg

# Verify rollback
kubectl get pods -n medkg
kubectl rollout status deployment/retrieval -n medkg
```

### Option 2: Image Tag Rollback

```bash
# Edit deployment to use previous image
kubectl set image deployment/retrieval retrieval=medkg/retrieval:v1.2.3 -n medkg

# Watch rollout
kubectl rollout status deployment/retrieval -n medkg
```

### Option 3: Full Terraform Rollback (Last Resort)

```bash
# Revert infrastructure changes
cd infra/terraform
git checkout HEAD~1
terraform apply -var-file=prod.tfvars
```

### Post-Rollback Verification

```bash
# Verify health
curl https://api.medkg.example.com/health

# Run E2E
python ops/e2e/run_verification.py --env production

# Monitor metrics for 30 minutes
```

## Troubleshooting

### Pods Not Starting

**Symptoms**: Pods in Pending or CrashLoopBackOff

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n medkg
kubectl logs <pod-name> -n medkg --previous
```

**Common Causes**:
- Image pull errors → Check registry credentials
- Resource limits too low → Increase limits
- Config errors → Verify ConfigMap
- Node capacity → Check node resources

### High Latency

**Symptoms**: P95 > 900ms

**Diagnosis**:
```bash
# Check OpenSearch latency
curl "https://opensearch:9200/_nodes/stats/indices/search"

# Check Neo4j latency
kubectl logs -n medkg <neo4j-pod> | grep "slow query"

# Check pod CPU/memory
kubectl top pods -n medkg
```

**Common Causes**:
- Slow queries → Optimize queries, add indexes
- Resource contention → Scale horizontally
- Network issues → Check inter-service latency

### Service Unavailable (503)

**Symptoms**: API returns 503

**Diagnosis**:
```bash
# Check pod health
kubectl get pods -n medkg

# Check dependencies
curl https://opensearch:9200/_cluster/health
curl http://neo4j:7474/db/data/
```

**Common Causes**:
- Dependency down → Restart service, check runbooks
- Too many requests → Scale up replicas
- Configuration error → Verify config, check logs

### Certificate Issues

**Symptoms**: TLS errors

**Diagnosis**:
```bash
kubectl describe certificate -n medkg
kubectl logs -n cert-manager deployment/cert-manager
```

**Resolution**:
```bash
# Delete and recreate certificate
kubectl delete certificate medkg-tls -n medkg
kubectl apply -f infra/k8s/ingress-prod.yaml
```

## Related Documentation

- [Operational Runbooks](../ops/runbooks/)
- [Configuration Guide](./configuration.md)
- [Monitoring Guide](./monitoring.md)
- [Security Guide](./security.md)
- [Incident Response Playbook](../ops/runbooks/05-incident-response.md)

## Support

For deployment issues:
1. Check runbooks: `ops/runbooks/`
2. Review logs: `kubectl logs -n medkg <pod>`
3. Contact on-call engineer: See PagerDuty
4. Escalate if needed: Follow incident response playbook
