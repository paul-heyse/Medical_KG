"""Lightweight configuration helpers and validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast


def validate_constraints(payload: Mapping[str, Any]) -> None:
    errors: list[str] = []
    _check_positive_numbers(payload, errors)
    _check_chunking(payload, errors)
    _check_retrieval(payload, errors)
    _check_pipelines(payload, errors)
    if errors:
        raise ValueError("; ".join(errors))


def _check_positive_numbers(payload: Mapping[str, Any], errors: list[str]) -> None:
    def assert_positive(value: Any, path: str) -> None:
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"{path} must be positive")

    sources = payload.get("sources", {})
    if not isinstance(sources, Mapping):
        return
    for source_name, source_obj in sources.items():
        if not isinstance(source_obj, Mapping):
            continue
        rate_raw = source_obj.get("rate_limit", {})
        rate = rate_raw if isinstance(rate_raw, Mapping) else {}
        assert_positive(rate.get("requests_per_minute"), f"sources.{source_name}.rate_limit.requests_per_minute")
        assert_positive(rate.get("burst"), f"sources.{source_name}.rate_limit.burst")
        retry_raw = source_obj.get("retry", {})
        retry = retry_raw if isinstance(retry_raw, Mapping) else {}
        assert_positive(retry.get("max_attempts"), f"sources.{source_name}.retry.max_attempts")
        assert_positive(retry.get("backoff_seconds"), f"sources.{source_name}.retry.backoff_seconds")


def _check_chunking(payload: Mapping[str, Any], errors: list[str]) -> None:
    chunking = payload.get("chunking", {})
    profiles = chunking.get("profiles", {}) if isinstance(chunking, Mapping) else {}
    if not isinstance(profiles, Mapping):
        return
    for name, profile in profiles.items():
        if not isinstance(profile, Mapping):
            continue
        target = profile.get("target_tokens")
        overlap = profile.get("overlap")
        if isinstance(target, int) and isinstance(overlap, int) and overlap >= target:
            errors.append(f"chunking.profiles.{name}.overlap must be less than target_tokens")


def _check_retrieval(payload: Mapping[str, Any], errors: list[str]) -> None:
    retrieval = payload.get("retrieval", {})
    if not isinstance(retrieval, Mapping):
        return
    fusion = retrieval.get("fusion", {})
    weights = fusion.get("weights", {}) if isinstance(fusion, Mapping) else {}
    if isinstance(weights, Mapping):
        total = sum(value for value in weights.values() if isinstance(value, (int, float)))
        if weights and abs(total - 1.0) > 0.01:
            errors.append("retrieval.fusion.weights must sum to 1.0±0.01")
    cache_raw = retrieval.get("cache", {})
    cache = cache_raw if isinstance(cache_raw, Mapping) else {}
    for field in ("query_seconds", "embedding_seconds", "expansion_seconds"):
        value = cache.get(field)
        if isinstance(value, int) and value <= 0:
            errors.append(f"retrieval.cache.{field} must be positive")


def _check_pipelines(payload: Mapping[str, Any], errors: list[str]) -> None:
    pipelines = payload.get("pipelines", {})
    pdf_container = pipelines.get("pdf", {}) if isinstance(pipelines, Mapping) else {}
    pdf = pdf_container if isinstance(pdf_container, Mapping) else {}
    ledger_path = pdf.get("ledger_path")
    artifact_dir = pdf.get("artifact_dir")
    if ledger_path and not isinstance(ledger_path, str):
        errors.append("pipelines.pdf.ledger_path must be a string path")
    if artifact_dir and not isinstance(artifact_dir, str):
        errors.append("pipelines.pdf.artifact_dir must be a string path")


@dataclass
class Config:
    payload: Mapping[str, Any]

    def feature_flags(self) -> dict[str, bool]:
        flags = self.payload.get("feature_flags", {})
        if isinstance(flags, Mapping):
            return {key: bool(value) for key, value in flags.items()}
        return {}

    def effective_fusion_weights(self) -> dict[str, float]:
        retrieval = cast(Mapping[str, Any], self.payload.get("retrieval", {}))
        fusion = cast(Mapping[str, Any], retrieval.get("fusion", {}))
        raw_weights = fusion.get("weights", {})
        weights: dict[str, float] = (
            {key: float(value) for key, value in raw_weights.items()}
            if isinstance(raw_weights, Mapping)
            else {}
        )
        feature_flags = self.payload.get("feature_flags", {})
        flags_mapping = feature_flags if isinstance(feature_flags, Mapping) else {}
        if not flags_mapping.get("splade_enabled", True):
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

    def breaking_changes(self, other: "Config") -> list[str]:
        breaking: list[str] = []
        embeddings = cast(Mapping[str, Any], self.payload.get("embeddings", {}))
        other_embeddings = cast(Mapping[str, Any], other.payload.get("embeddings", {}))
        if embeddings.get("vllm_api_base") != other_embeddings.get("vllm_api_base"):
            breaking.append("embeddings.vllm_api_base")
        kg = cast(Mapping[str, Any], self.payload.get("kg", {}))
        other_kg = cast(Mapping[str, Any], other.payload.get("kg", {}))
        if kg.get("neo4j_uri") != other_kg.get("neo4j_uri"):
            breaking.append("kg.neo4j_uri")
        return breaking

    def non_breaking_diff(self, other: "Config") -> dict[str, dict[str, Any]]:
        diff: dict[str, dict[str, Any]] = {}
        observability = cast(Mapping[str, Any], self.payload.get("observability", {}))
        other_observability = cast(Mapping[str, Any], other.payload.get("observability", {}))
        logging_cfg = cast(Mapping[str, Any], observability.get("logging", {}))
        other_logging = cast(Mapping[str, Any], other_observability.get("logging", {}))
        if logging_cfg.get("level") != other_logging.get("level"):
            diff.setdefault("observability.logging", {})["level"] = other_logging.get("level")
        retrieval = cast(Mapping[str, Any], self.payload.get("retrieval", {}))
        other_retrieval = cast(Mapping[str, Any], other.payload.get("retrieval", {}))
        if retrieval.get("fusion") != other_retrieval.get("fusion"):
            diff.setdefault("retrieval.fusion", {})["weights"] = other_retrieval.get("fusion", {}).get("weights")
        if self.feature_flags() != other.feature_flags():
            diff.setdefault("feature_flags", {})["values"] = other.feature_flags()
        return diff

    def auth_secret(self) -> str:
        return str(self.payload["apis"]["auth"]["jwt_secret"])

    def auth_settings(self) -> Mapping[str, Any]:
        apis = cast(Mapping[str, Any], self.payload.get("apis", {}))
        return cast(Mapping[str, Any], apis.get("auth", {}))

    def catalog_vocabs(self) -> Mapping[str, Any]:
        catalog = cast(Mapping[str, Any], self.payload.get("catalog", {}))
        return cast(Mapping[str, Any], catalog.get("vocabs", {}))

    def data(self) -> dict[str, Any]:
        return dict(self.payload)

    def retrieval_runtime(self) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], self.payload.get("retrieval", {}))

    def pdf_pipeline(self) -> Mapping[str, Any]:
        pipelines = cast(Mapping[str, Any], self.payload.get("pipelines", {}))
        return cast(Mapping[str, Any], pipelines.get("pdf", {}))

    def entity_linking(self) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], self.payload.get("entity_linking", {}))


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
