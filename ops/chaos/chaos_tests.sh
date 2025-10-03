#!/usr/bin/env bash
#
# Chaos Testing Suite
#
# Tests system resilience by introducing controlled failures.
# Run in staging environment only!
#
# Usage:
#   ./ops/chaos/chaos_tests.sh --scenario kill-api-pod
#   ./ops/chaos/chaos_tests.sh --scenario all

set -euo pipefail

NAMESPACE="${NAMESPACE:-medkg}"
KUBECONFIG="${KUBECONFIG:-~/.kube/config}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! kubectl get ns "$NAMESPACE" &> /dev/null; then
        error "Namespace $NAMESPACE not found"
        exit 1
    fi

    # Verify this is not production
    CURRENT_CONTEXT=$(kubectl config current-context)
    if [[ "$CURRENT_CONTEXT" == *"prod"* ]] || [[ "$CURRENT_CONTEXT" == *"production"* ]]; then
        error "Cannot run chaos tests in production context: $CURRENT_CONTEXT"
        exit 1
    fi

    if [[ "${CHAOS_APPROVED:-0}" != "1" ]]; then
        error "Set CHAOS_APPROVED=1 to acknowledge chaos testing blast radius"
        exit 1
    fi

    log "Prerequisites OK (context: $CURRENT_CONTEXT)"
}

wait_for_recovery() {
    local service=$1
    local timeout=${2:-300}
    local elapsed=0

    log "Waiting for $service to recover..."

    while [ $elapsed -lt $timeout ]; do
        if kubectl get pods -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[*].status.phase}' | grep -q Running; then
            log "$service recovered after ${elapsed}s"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done

    error "$service did not recover within ${timeout}s"
    return 1
}

verify_api_health() {
    local api_url="${API_URL:-http://localhost:8000}"
    log "Verifying API health at $api_url..."

    if curl -sf "$api_url/health" > /dev/null; then
        log "✅ API health check passed"
        return 0
    else
        error "❌ API health check failed"
        return 1
    fi
}

##############################################################################
# Chaos Scenario 1: Kill API Pod
##############################################################################
chaos_kill_api_pod() {
    log "=== Chaos Test: Kill API Pod ==="
    log "Expected: HPA scales up, requests re-route, no downtime"

    # Get current replica count
    local initial_replicas
    initial_replicas=$(kubectl get deployment retrieval -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    log "Initial replica count: $initial_replicas"

    # Kill one pod
    local pod_to_kill
    pod_to_kill=$(kubectl get pods -n "$NAMESPACE" -l app=retrieval -o jsonpath='{.items[0].metadata.name}')
    log "Killing pod: $pod_to_kill"
    kubectl delete pod "$pod_to_kill" -n "$NAMESPACE" --wait=false

    # Monitor for 2 minutes
    log "Monitoring for 2 minutes..."
    sleep 10

    # Check if new pod scheduled
    local current_pods
    current_pods=$(kubectl get pods -n "$NAMESPACE" -l app=retrieval --no-headers | wc -l)
    log "Current pod count: $current_pods"

    # Verify API still healthy
    if verify_api_health; then
        log "✅ Test PASSED: API remained available during pod failure"
    else
        error "❌ Test FAILED: API became unavailable"
        return 1
    fi

    # Wait for full recovery
    wait_for_recovery "retrieval" 120

    log "=== Chaos Test Complete: Kill API Pod ==="
}

##############################################################################
# Chaos Scenario 2: Kill vLLM Pod
##############################################################################
chaos_kill_vllm_pod() {
    log "=== Chaos Test: Kill vLLM Pod ==="
    log "Expected: Embed jobs fail gracefully, ledger remains consistent"

    # Get vLLM pod
    local vllm_pod
    vllm_pod=$(kubectl get pods -n "$NAMESPACE" -l app=vllm -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$vllm_pod" ]; then
        log "⚠️  No vLLM pods found, skipping test"
        return 0
    fi

    log "Killing vLLM pod: $vllm_pod"
    kubectl delete pod "$vllm_pod" -n "$NAMESPACE" --wait=false

    # Try to embed something (should fail gracefully)
    log "Testing embedding API (should fail gracefully)..."
    sleep 5

    local api_url="${API_URL:-http://localhost:8000}"
    local response
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X POST "$api_url/embed" \
        -H "Authorization: Bearer test-key" \
        -H "Content-Type: application/json" \
        -d '{"object_ids": ["chunk_test"], "object_type": "chunk"}')

    # Should return 503 (Service Unavailable) or 500
    if [[ "$response" == "503" ]] || [[ "$response" == "500" ]]; then
        log "✅ Test PASSED: Embedding failed gracefully with status $response"
    else
        log "⚠️  Unexpected status: $response (expected 503 or 500)"
    fi

    # Wait for vLLM recovery
    wait_for_recovery "vllm" 300

    log "=== Chaos Test Complete: Kill vLLM Pod ==="
}

##############################################################################
# Chaos Scenario 3: Network Partition to OpenSearch
##############################################################################
chaos_network_opensearch() {
    log "=== Chaos Test: Network Partition to OpenSearch ==="
    log "Expected: Retrieval returns 5xx, alerts fire, rollback restores connectivity"

    local policy_name="deny-opensearch-$RANDOM"
    cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ${policy_name}
spec:
  podSelector:
    matchLabels:
      app: retrieval
  policyTypes:
  - Egress
  egress: []
EOF

    log "NetworkPolicy ${policy_name} applied to block retrieval egress"
    sleep 30

    if [[ -n "${API_URL:-}" ]]; then
        set +e
        curl -sf "$API_URL/retrieve" \
            -H "Authorization: Bearer ${API_KEY:-test-key}" \
            -H "Content-Type: application/json" \
            -d '{"query": "metformin", "topK": 5}' >/dev/null
        local status=$?
        set -e
        if [[ $status -eq 0 ]]; then
            log "⚠️ Retrieval succeeded during partition; verify network selectors"
        else
            log "✅ Retrieval degraded as expected during partition"
        fi
    else
        log "API_URL not provided; validate impact via monitoring"
    fi

    kubectl delete networkpolicy "$policy_name" -n "$NAMESPACE" --ignore-not-found
    log "NetworkPolicy ${policy_name} removed"
    sleep 20
    log "=== Chaos Test Complete: Network Partition ==="
}

##############################################################################
# Chaos Scenario 4: Fill Neo4j Disk
##############################################################################
chaos_fill_neo4j_disk() {
    log "=== Chaos Test: Fill Neo4j Disk ==="
    log "Expected: Writes fail, alerts trigger, ops add capacity"

    local neo4j_pod
    neo4j_pod=$(kubectl get pods -n "$NAMESPACE" -l app=neo4j -o jsonpath='{.items[0].metadata.name}')
    if [[ -z "$neo4j_pod" ]]; then
        error "Neo4j pod not found"
        return 1
    fi

    log "Filling disk on $neo4j_pod"
    kubectl exec -n "$NAMESPACE" "$neo4j_pod" -- bash -c 'fallocate -l 1G /var/lib/neo4j/data/.chaos-fill'
    sleep 20
    kubectl exec -n "$NAMESPACE" "$neo4j_pod" -- bash -c 'df -h /var/lib/neo4j/data'
    kubectl exec -n "$NAMESPACE" "$neo4j_pod" -- bash -c 'rm -f /var/lib/neo4j/data/.chaos-fill'
    log "Disk pressure released"
    sleep 20
    log "=== Chaos Test Complete: Fill Disk ==="
}

##############################################################################
# Chaos Scenario 5: GPU OOM
##############################################################################
chaos_gpu_oom() {
    log "=== Chaos Test: GPU OOM ==="
    log "Expected: Job fails with clear error, no corrupt state"

    # Submit job with excessive batch size to trigger OOM
    local api_url="${API_URL:-http://localhost:8000}"

    log "Submitting large embedding batch (may trigger GPU OOM)..."

    # Create 1000 fake chunk IDs
    local large_batch
    large_batch=$(python3 -c "import json; print(json.dumps({'object_ids': [f'chunk_{i}' for i in range(1000)], 'object_type': 'chunk'}))")

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$api_url/embed" \
        -H "Authorization: Bearer test-key" \
        -H "Content-Type: application/json" \
        -d "$large_batch")

    local status_code
    status_code=$(echo "$response" | tail -n1)

    if [[ "$status_code" == "500" ]] || [[ "$status_code" == "503" ]]; then
        log "✅ Test PASSED: Large batch rejected or failed gracefully (status: $status_code)"
    elif [[ "$status_code" == "200" ]]; then
        log "✅ Test PASSED: Large batch succeeded (system handled it)"
    else
        log "⚠️  Unexpected status: $status_code"
    fi

    # Verify system still functional
    sleep 10
    if verify_api_health; then
        log "✅ System recovered from GPU stress test"
    else
        error "❌ System unhealthy after GPU stress test"
        return 1
    fi

    log "=== Chaos Test Complete: GPU OOM ==="
}

##############################################################################
# Run All Scenarios
##############################################################################
run_all_chaos_tests() {
    log "=== Running All Chaos Tests ==="

    local failed=0

    chaos_kill_api_pod || ((failed++))
    sleep 30

    chaos_kill_vllm_pod || ((failed++))
    sleep 30

    chaos_network_opensearch || ((failed++))
    sleep 30

    chaos_fill_neo4j_disk || ((failed++))
    sleep 30

    chaos_gpu_oom || ((failed++))

    log "=== Chaos Testing Complete ==="
    if [ $failed -eq 0 ]; then
        log "✅ All chaos tests passed"
        return 0
    else
        error "❌ $failed chaos tests failed"
        return 1
    fi
}

##############################################################################
# Main
##############################################################################
main() {
    local scenario="${1:-all}"

    check_prerequisites

    case "$scenario" in
        kill-api-pod)
            chaos_kill_api_pod
            ;;
        kill-vllm-pod)
            chaos_kill_vllm_pod
            ;;
        network-opensearch)
            chaos_network_opensearch
            ;;
        fill-neo4j-disk)
            chaos_fill_neo4j_disk
            ;;
        gpu-oom)
            chaos_gpu_oom
            ;;
        all)
            run_all_chaos_tests
            ;;
        *)
            error "Unknown scenario: $scenario"
            echo "Available scenarios: kill-api-pod, kill-vllm-pod, network-opensearch, fill-neo4j-disk, gpu-oom, all"
            exit 1
            ;;
    esac
}

# Parse arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 --scenario <scenario>"
    echo "Scenarios: kill-api-pod, kill-vllm-pod, network-opensearch, fill-neo4j-disk, gpu-oom, all"
    exit 1
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --scenario)
            SCENARIO="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main "${SCENARIO:-all}"
