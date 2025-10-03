# Scale Retrieval Runbook

## Purpose

Guide operators through scaling retrieval service to handle increased load.

## Prerequisites

- Kubernetes cluster access
- kubectl configured for target cluster
- Monitoring dashboard access

## Scaling Strategies

### Auto-Scaling (HPA)

The retrieval service has Horizontal Pod Autoscaler configured for CPU-based scaling.

#### View Current HPA Status

```bash
kubectl get hpa -n medkg retrieval-hpa

# Example output:
# NAME            REFERENCE              TARGETS   MINPODS   MAXPODS   REPLICAS
# retrieval-hpa   Deployment/retrieval   45%/70%   2         10        3
```

#### Adjust HPA Target CPU

```bash
# Edit HPA to change target CPU utilization
kubectl edit hpa retrieval-hpa -n medkg

# Change spec.targetCPUUtilizationPercentage
# For higher throughput, lower to 50%
# For cost savings, raise to 80%
```

### Request-Based Scaling (KEDA)

For request-bound workloads, use KEDA to scale based on RPS from Kafka lag.

#### View KEDA ScaledObject

```bash
kubectl get scaledobject -n medkg retrieval-scaler

# Check current scaling metrics
kubectl describe scaledobject retrieval-scaler -n medkg
```

#### Adjust RPS Threshold

```bash
# Edit ScaledObject
kubectl edit scaledobject retrieval-scaler -n medkg

# Change spec.triggers[0].metadata.lagThreshold
# Lower value = more aggressive scaling
# Higher value = fewer replicas
```

### Manual Scaling

For immediate scaling needs:

```bash
# Scale to specific replica count
kubectl scale deployment retrieval -n medkg --replicas=5

# Verify scaling
kubectl get pods -n medkg -l app=retrieval

# Wait for all pods to be Ready
kubectl wait --for=condition=Ready pod -l app=retrieval -n medkg --timeout=300s
```

## Performance Monitoring

### Check Current Load

```bash
# Query Prometheus for current RPS
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{service="retrieval"}[5m])' \
  | jq '.data.result[0].value[1]'

# Check P95 latency
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="retrieval"}[5m]))' \
  | jq '.data.result[0].value[1]'
```

### View Grafana Dashboard

1. Navigate to Grafana: <https://grafana.example.com>
2. Open "Retrieval Service" dashboard
3. Check panels:
   - Request Rate (RPS)
   - P50/P95/P99 Latency
   - CPU/Memory Utilization
   - Error Rate

## I/O Bound vs CPU Bound

### I/O Bound Indicators

- CPU utilization < 50%
- High wait time on OpenSearch/Neo4j
- Network throughput high

**Solution**: Scale horizontally with HPA

### CPU Bound Indicators

- CPU utilization > 70%
- Request queue growing
- Processing time increasing

**Solution**:

1. Scale horizontally (add replicas)
2. Consider vertical scaling (larger instance types)
3. Optimize query complexity

## Capacity Planning

### Calculate Required Replicas

```python
# Current metrics
current_rps = 100  # requests per second
current_replicas = 3
target_rps = 200  # desired throughput

# Linear scaling estimate
required_replicas = math.ceil((target_rps / current_rps) * current_replicas)
print(f"Estimated replicas needed: {required_replicas}")
```

### Pre-Scale for Known Events

```bash
# Before scheduled high-load event (e.g., demo, launch)
kubectl scale deployment retrieval -n medkg --replicas=8

# After event, scale down
kubectl scale deployment retrieval -n medkg --replicas=3
```

## Rollback

If scaling causes issues:

```bash
# Scale down to previous replica count
kubectl scale deployment retrieval -n medkg --replicas=3

# Check pod health
kubectl get pods -n medkg -l app=retrieval

# View recent pod events
kubectl get events -n medkg --sort-by='.lastTimestamp' | grep retrieval
```

## Common Issues

### Issue: Pods in CrashLoopBackOff

**Cause**: Resource limits too low, configuration error
**Solution**: Check pod logs, adjust resource limits

### Issue: OOMKilled pods

**Cause**: Memory limit too low for workload
**Solution**: Increase memory limits in deployment spec

### Issue: Slow scale-up

**Cause**: Image pull taking time, node capacity
**Solution**: Pre-pull images, add nodes to cluster

## Related

- [Hot Config Change Runbook](./01-hot-config-change.md)
- [Index Rebuild Runbook](./03-index-rebuild.md)
- [Performance Tuning Guide](../../docs/performance-tuning.md)
