"""Lightweight configuration helpers and validation."""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping


def validate_constraints(payload: Mapping[str, Any]) -> None:
    errors: List[str] = []
    _check_positive_numbers(payload, errors)
    _check_chunking(payload, errors)
    _check_retrieval(payload, errors)
    _check_pipelines(payload, errors)
    if errors:
        raise ValueError("; ".join(errors))


def _check_positive_numbers(payload: Mapping[str, Any], errors: List[str]) -> None:
    def assert_positive(value: Any, path: str) -> None:
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"{path} must be positive")

    for source_name, source in payload.get("sources", {}).items():
        rate = source.get("rate_limit", {})
        assert_positive(rate.get("requests_per_minute"), f"sources.{source_name}.rate_limit.requests_per_minute")
        assert_positive(rate.get("burst"), f"sources.{source_name}.rate_limit.burst")
        retry = source.get("retry", {})
        assert_positive(retry.get("max_attempts"), f"sources.{source_name}.retry.max_attempts")
        assert_positive(retry.get("backoff_seconds"), f"sources.{source_name}.retry.backoff_seconds")


def _check_chunking(payload: Mapping[str, Any], errors: List[str]) -> None:
    profiles = payload.get("chunking", {}).get("profiles", {})
    for name, profile in profiles.items():
        target = profile.get("target_tokens")
        overlap = profile.get("overlap")
        if isinstance(target, int) and isinstance(overlap, int) and overlap >= target:
            errors.append(f"chunking.profiles.{name}.overlap must be less than target_tokens")


def _check_retrieval(payload: Mapping[str, Any], errors: List[str]) -> None:
    retrieval = payload.get("retrieval", {})
    weights = retrieval.get("fusion", {}).get("weights", {})
    if weights:
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            errors.append("retrieval.fusion.weights must sum to 1.0±0.01")
    cache = retrieval.get("cache", {})
    for field in ("query_seconds", "embedding_seconds", "expansion_seconds"):
        value = cache.get(field)
        if isinstance(value, int) and value <= 0:
            errors.append(f"retrieval.cache.{field} must be positive")


def _check_pipelines(payload: Mapping[str, Any], errors: List[str]) -> None:
    pdf = payload.get("pipelines", {}).get("pdf", {})
    ledger_path = pdf.get("ledger_path")
    artifact_dir = pdf.get("artifact_dir")
    if ledger_path and not isinstance(ledger_path, str):
        errors.append("pipelines.pdf.ledger_path must be a string path")
    if artifact_dir and not isinstance(artifact_dir, str):
        errors.append("pipelines.pdf.artifact_dir must be a string path")


@dataclass
class Config:
    payload: Dict[str, Any]

    def feature_flags(self) -> Dict[str, bool]:
        return dict(self.payload.get("feature_flags", {}))

    def effective_fusion_weights(self) -> Dict[str, float]:
        weights = dict(self.payload["retrieval"]["fusion"]["weights"])
        if not self.payload["feature_flags"].get("splade_enabled", True):
            splade_weight = weights.pop("splade", 0.0)
            remainder_keys = ["bm25", "dense"]
            remainder_total = sum(weights.get(key, 0.0) for key in remainder_keys)
            if remainder_total == 0:
                for key in remainder_keys:
                    weights[key] = 0.5
            else:
                for key in remainder_keys:
                    weights[key] = weights.get(key, 0.0) + splade_weight * (
                        weights.get(key, 0.0) / remainder_total
                    )
            weights["splade"] = 0.0
        return weights

    def breaking_changes(self, other: "Config") -> List[str]:
        breaking: List[str] = []
        if self.payload["embeddings"]["vllm_api_base"] != other.payload["embeddings"]["vllm_api_base"]:
            breaking.append("embeddings.vllm_api_base")
        if self.payload["kg"]["neo4j_uri"] != other.payload["kg"]["neo4j_uri"]:
            breaking.append("kg.neo4j_uri")
        return breaking

    def non_breaking_diff(self, other: "Config") -> Dict[str, Dict[str, Any]]:
        diff: Dict[str, Dict[str, Any]] = {}
        if self.payload["observability"]["logging"]["level"] != other.payload["observability"]["logging"]["level"]:
            diff.setdefault("observability.logging", {})["level"] = other.payload["observability"]["logging"]["level"]
        if self.payload["retrieval"]["fusion"]["weights"] != other.payload["retrieval"]["fusion"]["weights"]:
            diff.setdefault("retrieval.fusion", {})["weights"] = other.payload["retrieval"]["fusion"]["weights"]
        if self.feature_flags() != other.feature_flags():
            diff.setdefault("feature_flags", {})["values"] = other.feature_flags()
        return diff

    def auth_secret(self) -> str:
        return str(self.payload["apis"]["auth"]["jwt_secret"])

    def auth_settings(self) -> Mapping[str, Any]:
        return self.payload["apis"]["auth"]

    def catalog_vocabs(self) -> Mapping[str, Any]:
        return self.payload["catalog"]["vocabs"]

    def data(self) -> Dict[str, Any]:
        return self.payload

    def retrieval_runtime(self) -> Mapping[str, Any]:
        return self.payload["retrieval"]

    def pdf_pipeline(self) -> Mapping[str, Any]:
        return self.payload["pipelines"]["pdf"]

    def entity_linking(self) -> Mapping[str, Any]:
        return self.payload["entity_linking"]


@dataclass
class PolicyDocument:
    vocabs: Mapping[str, Mapping[str, Any]]
    actions: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PolicyDocument":
        if "vocabs" not in data or "actions" not in data:
            raise ValueError("policy.yaml must define vocabs and actions")
        return cls(vocabs=data["vocabs"], actions=data["actions"])


__all__ = ["Config", "validate_constraints", "PolicyDocument"]
