"""High-level planner for infrastructure artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, MutableMapping

import yaml

from .models import DeploymentTarget, EnvironmentConfig, ServiceConfig, summarize_services


@dataclass(slots=True)
class InfrastructurePlanner:
    """Produces Kubernetes, Helm, Terraform, and monitoring plans."""

    target: DeploymentTarget
    environment: EnvironmentConfig

    def kubernetes_manifests(self) -> Mapping[str, list[Mapping[str, object]]]:
        manifests: MutableMapping[str, list[Mapping[str, object]]] = {
            "deployments": [],
            "services": [],
            "configmaps": [],
            "secrets": [],
            "hpas": [],
            "pdbs": [],
            "ingress": [],
            "rbac": [],
        }
        for service in self.target.services:
            manifests["deployments"].append(self._deployment(service))
            manifests["services"].append(self._service(service))
            manifests["configmaps"].append(self._configmap(service))
            manifests["secrets"].append(self._secret(service))
            manifests["hpas"].append(self._hpa(service))
            manifests["pdbs"].append(self._pdb(service))
            manifests["rbac"].append(self._rbac(service))
        manifests["ingress"].append(self._ingress())
        return manifests

    def helm_values(self) -> Mapping[str, object]:
        base_values = {
            "global": {
                "domain": self.environment.domain,
                "bucketPrefix": self.environment.bucket_prefix,
            },
            "services": summarize_services(self.target.services),
            "rateLimits": self.environment.rate_limits,
        }
        return {
            "chart": {
                "apiVersion": "v2",
                "name": f"medkg-{self.target.name}",
                "version": "0.1.0",
            },
            "values": base_values,
            "overrides": {env: self._env_overrides(env) for env in ("dev", "staging", "prod")},
        }

    def terraform_modules(self) -> Mapping[str, object]:
        return {
            "vpc": {"cidr_block": "10.0.0.0/16", "public_subnets": 2, "private_subnets": 4},
            "eks": {
                "cluster_name": f"medkg-{self.environment.name}",
                "gpu_node_groups": [profile.name for profile in self.target.gpu_profiles],
            },
            "opensearch": {"nodes": 3, "snapshots": True},
            "neo4j": {"replicas": 3, "backups": True},
            "redis": {"replicas": 2},
            "vault": {"enabled": True},
            "s3": {
                "buckets": [
                    f"{self.environment.bucket_prefix}-raw",
                    f"{self.environment.bucket_prefix}-artifacts",
                    f"{self.environment.bucket_prefix}-backups",
                ]
            },
        }

    def monitoring_plan(self) -> Mapping[str, object]:
        return {
            "prometheus": {
                "scrape_interval": "10s",
                "retention": "30d",
                "service_monitors": [
                    {"name": svc.name, "path": svc.metrics_path} for svc in self.target.services
                ],
            },
            "grafana": {
                "dashboards": ["retrieval", "gpu", "ingestion", "extraction", "kg", "api"],
            },
            "alerting": {
                "provider": "pagerduty",
                "webhook": self.environment.alert_webhook,
                "severities": {"P1": "service_down", "P2": "slo_breach", "P3": "warning"},
            },
        }

    def ci_pipeline(self) -> Mapping[str, object]:
        return {
            "lint": ["ruff", "black", "mypy"],
            "tests": ["pytest", "evaluation-smoke"],
            "build": [svc.name for svc in self.target.services],
            "deploy": {"staging": "helm upgrade", "prod": "manual-approval"},
        }

    def render_yaml(self, manifest: Mapping[str, object]) -> str:
        return yaml.safe_dump(manifest, sort_keys=True)

    def _deployment(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": service.name, "namespace": self.environment.namespace},
            "spec": {
                "replicas": service.replicas,
                "selector": {"matchLabels": {"app": service.name}},
                "template": {
                    "metadata": {"labels": {"app": service.name}},
                    "spec": {
                        "containers": [
                            {
                                "name": service.name,
                                "image": service.image,
                                "ports": [{"containerPort": port} for port in service.ports],
                                "env": [
                                    {"name": key, "value": value}
                                    for key, value in service.env.items()
                                ],
                                "resources": {
                                    "requests": {"cpu": service.cpu, "memory": service.memory},
                                    "limits": {
                                        key: value
                                        for key, value in {
                                            "cpu": service.cpu,
                                            "memory": service.memory,
                                            "nvidia.com/gpu": service.gpu,
                                        }.items()
                                        if value is not None
                                    },
                                },
                            }
                        ],
                    },
                },
            },
        }

    def _service(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": service.name, "namespace": self.environment.namespace},
            "spec": {
                "selector": {"app": service.name},
                "ports": [{"port": port, "targetPort": port} for port in service.ports],
                "type": "ClusterIP",
            },
        }

    def _configmap(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": f"{service.name}-config"},
            "data": {"service": service.name},
        }

    def _secret(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": f"{service.name}-secrets"},
            "type": "Opaque",
            "data": {},
        }

    def _hpa(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": f"{service.name}-hpa"},
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": service.name,
                },
                "minReplicas": max(1, service.replicas // 2),
                "maxReplicas": service.replicas * 3,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {"type": "Utilization", "averageUtilization": 60},
                        },
                    }
                ],
            },
        }

    def _pdb(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {"name": f"{service.name}-pdb"},
            "spec": {
                "minAvailable": max(1, service.replicas - 1),
                "selector": {"matchLabels": {"app": service.name}},
            },
        }

    def _rbac(self, service: ServiceConfig) -> Mapping[str, object]:
        return {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": {"name": f"{service.name}-role"},
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["configmaps"],
                    "verbs": ["get", "list"],
                }
            ],
        }

    def _ingress(self) -> Mapping[str, object]:
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {"name": "medkg", "namespace": self.environment.namespace},
            "spec": {
                "ingressClassName": "alb",
                "tls": [
                    {"hosts": [self.environment.domain], "secretName": self.environment.tls_secret}
                ],
                "rules": [
                    {
                        "host": self.environment.domain,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": svc.name,
                                            "port": {"number": svc.ports[0]},
                                        }
                                    },
                                }
                                for svc in self.target.services
                            ],
                        },
                    }
                ],
            },
        }

    def _env_overrides(self, env: str) -> Mapping[str, object]:
        multiplier = {"dev": 0.5, "staging": 1.0, "prod": 1.5}[env]
        overrides = []
        for svc in self.target.services:
            overrides.append(
                {
                    "name": svc.name,
                    "replicas": max(1, int(svc.replicas * multiplier)),
                }
            )
        return {"services": overrides}


__all__ = ["InfrastructurePlanner"]
