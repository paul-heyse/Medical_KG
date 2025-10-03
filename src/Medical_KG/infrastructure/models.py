"""Dataclasses describing infrastructure configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class GPUProfile:
    name: str
    label: str
    taints: Mapping[str, str] = field(default_factory=dict)
    resources: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ServiceConfig:
    name: str
    image: str
    replicas: int = 2
    cpu: str = "500m"
    memory: str = "1Gi"
    gpu: str | None = None
    ports: Sequence[int] = field(default_factory=lambda: [80])
    env: Mapping[str, str] = field(default_factory=dict)
    metrics_path: str = "/metrics"
    scopes: Sequence[str] = field(default_factory=list)


@dataclass(slots=True)
class DeploymentTarget:
    name: str
    services: Sequence[ServiceConfig]
    gpu_profiles: Sequence[GPUProfile] = field(default_factory=list)


@dataclass(slots=True)
class EnvironmentConfig:
    name: str
    namespace: str
    domain: str
    tls_secret: str
    rate_limits: Mapping[str, int]
    bucket_prefix: str
    alert_webhook: str


def summarize_services(services: Sequence[ServiceConfig]) -> list[MutableMapping[str, object]]:
    summary: list[MutableMapping[str, object]] = []
    for svc in services:
        summary.append(
            {
                "name": svc.name,
                "image": svc.image,
                "replicas": svc.replicas,
                "resources": {"cpu": svc.cpu, "memory": svc.memory, "gpu": svc.gpu},
                "ports": list(svc.ports),
            }
        )
    return summary


__all__ = [
    "GPUProfile",
    "ServiceConfig",
    "DeploymentTarget",
    "EnvironmentConfig",
    "summarize_services",
]
