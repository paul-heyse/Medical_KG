# GPU Node Failure Runbook

## Purpose

Guide operators through handling GPU node failures and restoring GPU-based services.

## Prerequisites

- Kubernetes cluster access
- Node admin access
- GPU monitoring dashboard access

## Symptoms

- vLLM pods in Pending or CrashLoopBackOff
- GPU visibility errors in logs
- Embedding jobs failing
- Alert: "GPU not visible" or "vLLM down"

## Diagnosis

### 1. Check GPU Node Status

```bash
# List all GPU nodes
kubectl get nodes -l node-type=gpu -o wide

# Check node conditions
kubectl describe node <gpu-node-name> | grep -A 20 Conditions

# Common issues:
# - NotReady
# - MemoryPressure
# - DiskPressure
# - PIDPressure
```

### 2. Check GPU Device Plugin

```bash
# Verify NVIDIA device plugin running
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Check GPU allocatable resources
kubectl describe node <gpu-node-name> | grep -A 5 "Allocatable:"
# Should show nvidia.com/gpu: 1 (or more)
```

### 3. Check Pod Status

```bash
# Check vLLM pods
kubectl get pods -n medkg -l app=vllm -o wide

# View pod events
kubectl describe pod <vllm-pod-name> -n medkg

# Check logs
kubectl logs <vllm-pod-name> -n medkg --tail=100
```

## Resolution

### Immediate Guardrails

- Pause chaos experiments or GPU-intensive jobs.
- Annotate node with `medkg.io/cordon-reason=gpu-incident` for audit trail:

```bash
kubectl annotate node <gpu-node-name> medkg.io/cordon-reason="gpu-incident-$(date -u +%Y%m%dT%H%M%S)"
```

### Scenario A: Node NotReady (Software Issue)

#### 1. Cordon Node

```bash
# Prevent new pods from scheduling
kubectl cordon <gpu-node-name>

# Verify
kubectl get nodes | grep <gpu-node-name>
# Should show SchedulingDisabled
```

#### 2. Drain Pods

```bash
# Gracefully evict pods
kubectl drain <gpu-node-name> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --force \
  --grace-period=300

# Verify all pods moved
kubectl get pods -n medkg -o wide | grep <gpu-node-name>
```

#### 3. SSH to Node and Diagnose

```bash
# SSH to GPU node
ssh admin@<gpu-node-ip>

# Check GPU visibility
nvidia-smi

# Expected output: GPU list with utilization
# If command fails: GPU driver issue

# Check CUDA
nvcc --version

# Check Docker can access GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

#### 4. Restart GPU Services

```bash
# On GPU node
sudo systemctl restart nvidia-persistenced
sudo systemctl restart docker

# Verify GPU accessible
nvidia-smi
```

#### 5. Uncordon Node

```bash
# From kubectl control machine
kubectl uncordon <gpu-node-name>

# Verify node Ready
kubectl get nodes | grep <gpu-node-name>
```

#### 6. Verify Pod Scheduling

```bash
# Wait for vLLM pods to schedule
kubectl get pods -n medkg -l app=vllm -o wide -w

# Check GPU allocated
kubectl describe pod <vllm-pod-name> -n medkg | grep "nvidia.com/gpu"
```

### Scenario B: Hardware Failure

#### 1. Cordon and Drain (as above)

#### 2. Mark Node for Maintenance

```bash
# Add maintenance label
kubectl label node <gpu-node-name> maintenance=true

# Add taint to prevent scheduling
kubectl taint node <gpu-node-name> maintenance=true:NoSchedule
```

#### 3. Open Hardware Ticket

- Cloud: Create support ticket for GPU instance replacement
- On-prem: Engage datacenter team for hardware replacement

#### 4. Provision Replacement Node

```bash
# Using Terraform (if infrastructure as code)
cd infra/terraform
terraform apply -target=aws_instance.gpu_node_2

# Or manually provision via cloud console
```

#### 5. Remove Failed Node

```bash
# After replacement provisioned
kubectl delete node <old-gpu-node-name>

# Verify new node joined
kubectl get nodes -l node-type=gpu
```

### Scenario C: vLLM Service Issue (GPU Healthy)

#### 1. Check vLLM Health Endpoint

```bash
# Port-forward to vLLM
kubectl port-forward -n medkg svc/vllm 8000:8000 &

# Check health
curl http://localhost:8000/health

# Expected: {"status": "ok"}
```

#### 2. Check vLLM Logs

```bash
kubectl logs -n medkg -l app=vllm --tail=200

# Common errors:
# - CUDA out of memory
# - Model loading timeout
# - Port already in use
```

#### 3. Restart vLLM Pods

```bash
# Delete pods (deployment will recreate)
kubectl delete pods -n medkg -l app=vllm

# Watch recreation
kubectl get pods -n medkg -l app=vllm -w

# Wait for Ready
kubectl wait --for=condition=Ready pod -l app=vllm -n medkg --timeout=600s
```

#### 4. Verify Embedding & vLLM Services

```bash
# Test embedding via API (tokens < 1024 to stay within default batch limits)
curl -X POST https://api.medkg.example.com/embed \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "X-Request-ID: gpu-recovery-test" \
  -d '{
    "object_ids": ["chunk_12345"],
    "object_type": "chunk"
  }'

# Expected: {"embedded_count": 1, "failed": []}

# Test vLLM completions (briefing generation)
curl -X POST https://api.medkg.example.com/briefing \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "query": "metformin cardiovascular outcomes",
    "format": "markdown",
    "max_tokens": 600
  }' | jq '.content | length'

# Expected: content length > 400 characters, citations present
```

## Monitoring

### Check GPU Utilization

```bash
# Query Prometheus
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=gpu_utilization_percent' \
  | jq '.data.result'

# Target: 80-90% under load
```

### Check Embedding Throughput

```bash
# Tokens per second per GPU
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(embedding_tokens_total[5m]) / gpu_count' \
  | jq '.data.result[0].value[1]'

# Target: ≥2,500 tokens/s/GPU for Qwen
```

## Prevention

### Pre-Flight Checks

Before deploying GPU workloads:

```bash
# Verify GPU plugin installed
kubectl get ds -n kube-system nvidia-device-plugin-ds

# Verify GPU capacity
kubectl describe nodes -l node-type=gpu | grep "nvidia.com/gpu:"

# Test GPU with job
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: gpu-test
spec:
  template:
    spec:
      containers:
      - name: cuda
        image: nvidia/cuda:11.8.0-base-ubuntu22.04
        command: ["nvidia-smi"]
        resources:
          limits:
            nvidia.com/gpu: 1
      restartPolicy: Never
EOF

# Check results
kubectl logs job/gpu-test
kubectl delete job gpu-test
```

### Monitoring Alerts

Ensure alerts configured:

```yaml
# prometheus-alerts.yaml
groups:
  - name: gpu
    rules:
      - alert: GPUNodeDown
        expr: kube_node_status_condition{node=~".*gpu.*", condition="Ready", status="false"} == 1
        for: 5m
        annotations:
          summary: "GPU node {{ $labels.node }} is NotReady"

      - alert: VLLMDown
        expr: up{job="vllm"} == 0
        for: 2m
        annotations:
          summary: "vLLM service is down"

      - alert: GPUNotVisible
        expr: gpu_count == 0
        for: 5m
        annotations:
          summary: "No GPUs visible to monitoring"
```

## Related

- [vLLM Service Troubleshooting](./05-vllm-troubleshooting.md)
- [Embedding Pipeline Guide](../../docs/embeddings_gpu.md)
- [Infrastructure Documentation](../../docs/infrastructure.md)
