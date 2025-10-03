from __future__ import annotations

from Medical_KG.infrastructure import (
    DeploymentTarget,
    EnvironmentConfig,
    GPUProfile,
    InfrastructurePlanner,
    ServiceConfig,
)


def _sample_target() -> DeploymentTarget:
    services = [
        ServiceConfig(
            name="api", image="ghcr.io/medkg/api:latest", replicas=2, cpu="750m", memory="2Gi"
        ),
        ServiceConfig(
            name="ingest", image="ghcr.io/medkg/ingest:latest", replicas=1, cpu="500m", memory="1Gi"
        ),
    ]
    gpu_profiles = [
        GPUProfile(
            name="vllm", label="gpu=a100", taints={"gpu": "true"}, resources={"nvidia.com/gpu": "1"}
        )
    ]
    return DeploymentTarget(name="core", services=services, gpu_profiles=gpu_profiles)


def _sample_env() -> EnvironmentConfig:
    return EnvironmentConfig(
        name="dev",
        namespace="medkg-dev",
        domain="dev.medkg.ai",
        tls_secret="medkg-dev-tls",
        rate_limits={"default": 100, "qa": 30},
        bucket_prefix="medkg-dev",
        alert_webhook="https://pagerduty.example.com/webhook",
    )


def test_kubernetes_manifests_cover_expected_sections() -> None:
    planner = InfrastructurePlanner(target=_sample_target(), environment=_sample_env())
    manifests = planner.kubernetes_manifests()
    assert set(manifests) == {
        "deployments",
        "services",
        "configmaps",
        "secrets",
        "hpas",
        "pdbs",
        "ingress",
        "rbac",
    }
    assert manifests["deployments"][0]["kind"] == "Deployment"
    rendered = planner.render_yaml(manifests["deployments"][0])
    assert "apiVersion" in rendered


def test_helm_values_include_overrides() -> None:
    planner = InfrastructurePlanner(target=_sample_target(), environment=_sample_env())
    values = planner.helm_values()
    assert values["chart"]["name"] == "medkg-core"
    assert set(values["overrides"]) == {"dev", "staging", "prod"}


def test_monitoring_plan_and_ci_pipeline() -> None:
    planner = InfrastructurePlanner(target=_sample_target(), environment=_sample_env())
    monitoring = planner.monitoring_plan()
    assert monitoring["prometheus"]["service_monitors"][0]["name"] == "api"
    pipeline = planner.ci_pipeline()
    assert "api" in pipeline["build"]


def test_terraform_modules_reference_gpu_profile() -> None:
    planner = InfrastructurePlanner(target=_sample_target(), environment=_sample_env())
    modules = planner.terraform_modules()
    assert modules["eks"]["gpu_node_groups"] == ["vllm"]
