# GPU / Compute Cost Optimisation

## Policies

- **Auto-shutdown** idle GPU nodes after 30 minutes (Cluster Autoscaler + node auto-provisioner).
- **Spot instances** for stateless embedding workers with checkpoint restart; production inference remains on on-demand nodes.
- **Quota alarms** on GPU spend via cloud billing alerts (weekly cap, monthly budget).
- **Batch windows** – schedule embedding backfills during off-peak hours, scale down overnight.

## Implementation

1. **Cluster Autoscaler** – enable scale-down on GPU node group (`--scale-down-utilization-threshold=0.4`).
2. **Karpenter / Node Autoprovisioner** – provision GPU spot nodes with taints (`spot=true:NoSchedule`) consumed by embedding jobs.
3. **Idle detection** – CronJob runs `nvidia-smi --query-compute-apps` and scales deployments to zero if idle.
4. **vLLM Settings** – set `max_num_batched_tokens` and `tensor_parallel_size` to balance throughput vs memory.
5. **Observability** – Grafana `GPU Utilization` dashboard overlays utilisation vs cost budgets.

## Review Cadence

- Weekly GPU cost review with Ops + Finance.
- Monthly rightsizing based on utilisation percentiles.
- Post-incident reviews for GPU OOM events feed back into taints/requests.
