# Load Testing Suite

Comprehensive load testing for Medical KG API using Locust.

## Prerequisites

```bash
pip install locust
```

## Test Scenarios

### 1. Burst Scenario (50 QPS for 2 minutes)

Tests system behavior under sudden traffic spike.

```bash
locust -f ops/load_test/locustfile.py \
    --headless \
    --users 50 \
    --spawn-rate 10 \
    --run-time 2m \
    --host https://api-staging.medkg.example.com \
    --html ops/load_test/reports/burst_report.html
```

**Expected Metrics**:

- P95 latency `/retrieve`: < 900ms
- P95 latency `/extract`: < 2000ms
- Error rate: < 1%
- All 50 users spawn successfully

### 2. Steady Scenario (10 QPS for 1 hour)

Tests system stability under sustained load.

```bash
locust -f ops/load_test/locustfile.py \
    --headless \
    --users 10 \
    --spawn-rate 2 \
    --run-time 1h \
    --host https://api-staging.medkg.example.com \
    --html ops/load_test/reports/steady_report.html
```

**Expected Metrics**:

- P95 latency `/retrieve`: < 800ms
- Memory: No growth over time (no leaks)
- CPU: Stable utilization
- Error rate: < 0.5%

### 3. Mixed Intent Distribution

Default test with realistic intent distribution (built into locustfile.py):

- Endpoint queries: 40%
- Adverse event queries: 25%
- Dose queries: 15%
- Eligibility queries: 10%
- General queries: 10%

### 4. Ramp-Up Test

Gradually increase load to find breaking point.

```bash
locust -f ops/load_test/locustfile.py \
    --headless \
    --users 100 \
    --spawn-rate 1 \
    --run-time 10m \
    --host https://api-staging.medkg.example.com
```

Monitor when P95 latency exceeds SLO (900ms).

## Running Interactively

For real-time monitoring and adjustments:

```bash
locust -f ops/load_test/locustfile.py \
    --host https://api-staging.medkg.example.com

# Open browser to http://localhost:8089
# Configure users and spawn rate in UI
```

## Performance Targets

### Latency SLOs

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| `/retrieve` | 300ms | 900ms | 1500ms |
| `/extract/*` | 800ms | 2000ms | 3000ms |
| `/facets/generate` | 600ms | 1800ms | 2500ms |
| `/health` | 10ms | 50ms | 100ms |

### Throughput Targets

- Retrieve: 50+ QPS sustained
- Extract: 20+ QPS sustained
- Facets: 10+ QPS sustained

### Resource Utilization

- CPU: < 70% average during steady load
- Memory: Stable, no leaks
- GPU: 80-90% utilization under load

## Analyzing Results

### Locust HTML Report

Open generated HTML report for:

- Request distribution
- Response time percentiles
- Failures breakdown
- Charts over time

### Prometheus Queries

While test running, query metrics:

```bash
# P95 latency
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="retrieval"}[1m]))' \
  | jq '.data.result[0].value[1]'

# Error rate
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{code=~"5.."}[1m]) / rate(http_requests_total[1m])' \
  | jq '.data.result[0].value[1]'

# Request rate
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total[1m])' \
  | jq '.data.result[0].value[1]'
```

### Grafana Dashboard

1. Navigate to Grafana: <https://grafana.example.com>
2. Open "Load Test" dashboard
3. Set time range to test duration
4. Analyze:
   - Latency trends
   - Error spikes
   - Resource utilization
   - Throughput

## Flamegraph Analysis

To identify bottlenecks, capture flamegraphs during load test:

```bash
# Install py-spy
pip install py-spy

# Profile API process during load test
sudo py-spy record -o ops/load_test/flamegraph.svg --pid <api-process-pid> --duration 60

# View flamegraph.svg to identify hotspots
```

## Back-Pressure Handling

If P95 exceeds SLO, system should gracefully degrade:

1. Disable reranker (saves 200-300ms)
2. Reduce topK from 20 to 10
3. Switch fusion from weighted to RRF (simpler, faster)

Test degradation:

```bash
# Enable degradation mode
curl -X POST https://api-staging.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}"

# Re-run load test
locust -f ops/load_test/locustfile.py --headless --users 50 --run-time 2m

# Verify latency improved
```

## Troubleshooting

### High Latency

- **Check OpenSearch**: Slow queries?
- **Check Neo4j**: Vector search slow?
- **Check GPU**: vLLM responsive?
- **Check Network**: High inter-service latency?

### High Error Rate

- **Check Logs**: What errors occurring?
- **Check Resources**: OOM? CPU throttling?
- **Check Dependencies**: Downstream service down?

### Memory Leaks

- **Monitor Memory**: Over time, does it grow?
- **Heap Dump**: Capture and analyze
- **Profile**: Use memory profiler

## CI Integration

Add to GitHub Actions:

```yaml
# .github/workflows/load-test.yml
name: Load Test

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Locust
        run: pip install locust

      - name: Run Load Test
        run: |
          locust -f ops/load_test/locustfile.py \
            --headless \
            --users 10 \
            --spawn-rate 2 \
            --run-time 5m \
            --host https://api-staging.medkg.example.com \
            --html load_test_report.html

      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: load-test-report
          path: load_test_report.html

      - name: Check Performance
        run: |
          # Parse report and fail if P95 > threshold
          # (implementation depends on output format)
          python ops/load_test/check_thresholds.py load_test_report.html
```

## Related

- [Performance Tuning Guide](../../docs/performance-tuning.md)
- [Monitoring Guide](../../docs/monitoring.md)
- [Scale Retrieval Runbook](../runbooks/02-scale-retrieval.md)
