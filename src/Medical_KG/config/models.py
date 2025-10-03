"""Typed configuration models and helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from Medical_KG.types import JSONMapping, JSONValue


def validate_constraints(payload: JSONMapping) -> None:
    errors: list[str] = []
    _check_positive_numbers(payload, errors)
    _check_chunking(payload, errors)
    _check_retrieval(payload, errors)
    _check_pipelines(payload, errors)
    if errors:
        raise ValueError("; ".join(errors))


def _check_positive_numbers(payload: JSONMapping, errors: list[str]) -> None:
    def assert_positive(value: JSONValue | None, path: str) -> None:
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"{path} must be positive")

    sources = _as_mapping(payload.get("sources"))
    for source_name, source_obj in sources.items():
        source_mapping = _as_mapping(source_obj)
        rate = _as_mapping(source_mapping.get("rate_limit"))
        assert_positive(
            rate.get("requests_per_minute"),
            f"sources.{source_name}.rate_limit.requests_per_minute",
        )
        assert_positive(rate.get("burst"), f"sources.{source_name}.rate_limit.burst")
        retry = _as_mapping(source_mapping.get("retry"))
        assert_positive(
            retry.get("max_attempts"), f"sources.{source_name}.retry.max_attempts"
        )
        assert_positive(
            retry.get("backoff_seconds"), f"sources.{source_name}.retry.backoff_seconds"
        )


def _check_chunking(payload: JSONMapping, errors: list[str]) -> None:
    chunking = _as_mapping(payload.get("chunking"))
    profiles = _as_mapping(chunking.get("profiles"))
    for name, profile in profiles.items():
        profile_mapping = _as_mapping(profile)
        target = profile_mapping.get("target_tokens")
        overlap = profile_mapping.get("overlap")
        if isinstance(target, int) and isinstance(overlap, int) and overlap >= target:
            errors.append(f"chunking.profiles.{name}.overlap must be less than target_tokens")


def _check_retrieval(payload: JSONMapping, errors: list[str]) -> None:
    retrieval = _as_mapping(payload.get("retrieval"))
    fusion = _as_mapping(retrieval.get("fusion"))
    weights = _as_mapping(fusion.get("weights"))
    numeric_weights = [value for value in weights.values() if isinstance(value, (int, float))]
    if weights and numeric_weights:
        total = sum(float(value) for value in numeric_weights)
        if abs(total - 1.0) > 0.01:
            errors.append("retrieval.fusion.weights must sum to 1.0±0.01")
    cache = _as_mapping(retrieval.get("cache"))
    for field in ("query_seconds", "embedding_seconds", "expansion_seconds"):
        value = cache.get(field)
        if isinstance(value, int) and value <= 0:
            errors.append(f"retrieval.cache.{field} must be positive")


def _check_pipelines(payload: JSONMapping, errors: list[str]) -> None:
    pipelines = _as_mapping(payload.get("pipelines"))
    pdf = _as_mapping(pipelines.get("pdf"))
    ledger_path = pdf.get("ledger_path")
    artifact_dir = pdf.get("artifact_dir")
    if ledger_path and not isinstance(ledger_path, str):
        errors.append("pipelines.pdf.ledger_path must be a string path")
    if artifact_dir and not isinstance(artifact_dir, str):
        errors.append("pipelines.pdf.artifact_dir must be a string path")


def _as_mapping(value: JSONValue | None) -> Mapping[str, JSONValue]:
    if isinstance(value, Mapping):
        return value
    return {}


@dataclass(frozen=True)
class AuthSettings:
    issuer: str
    audience: str
    admin_scope: str


@dataclass(frozen=True)
class AuthConfig:
    jwt_secret: str
    settings: AuthSettings


@dataclass(frozen=True)
class PdfPipelineSettings:
    ledger_path: Path
    artifact_dir: Path
    require_gpu: bool


@dataclass
class Config:
    payload: JSONMapping

    def feature_flags(self) -> dict[str, bool]:
        flags = _as_mapping(self.payload.get("feature_flags"))
        return {key: bool(value) for key, value in flags.items()}

    def effective_fusion_weights(self) -> dict[str, float]:
        retrieval = _as_mapping(self.payload.get("retrieval"))
        fusion = _as_mapping(retrieval.get("fusion"))
        raw_weights = _as_mapping(fusion.get("weights"))
        weights: dict[str, float] = {
            key: float(value)
            for key, value in raw_weights.items()
            if isinstance(value, (int, float))
        }
        feature_flags = _as_mapping(self.payload.get("feature_flags"))
        if not feature_flags.get("splade_enabled", True):
            splade_weight = weights.pop("splade", 0.0)
            remainder_keys = ["bm25", "dense"]
            remainder_total = sum(weights.get(key, 0.0) for key in remainder_keys)
            if remainder_total == 0:
                for key in remainder_keys:
                    weights[key] = 0.5
            else:
                for key in remainder_keys:
                    current = weights.get(key, 0.0)
                    weights[key] = current + splade_weight * (current / remainder_total if remainder_total else 0)
            weights["splade"] = 0.0
        return weights

    def breaking_changes(self, other: "Config") -> list[str]:
        breaking: list[str] = []
        embeddings = _as_mapping(self.payload.get("embeddings"))
        other_embeddings = _as_mapping(other.payload.get("embeddings"))
        if embeddings.get("vllm_api_base") != other_embeddings.get("vllm_api_base"):
            breaking.append("embeddings.vllm_api_base")
        kg = _as_mapping(self.payload.get("kg"))
        other_kg = _as_mapping(other.payload.get("kg"))
        if kg.get("neo4j_uri") != other_kg.get("neo4j_uri"):
            breaking.append("kg.neo4j_uri")
        return breaking

    def non_breaking_diff(self, other: "Config") -> dict[str, dict[str, JSONValue]]:
        diff: dict[str, dict[str, JSONValue]] = {}
        observability = _as_mapping(self.payload.get("observability"))
        other_observability = _as_mapping(other.payload.get("observability"))
        logging_cfg = _as_mapping(observability.get("logging"))
        other_logging = _as_mapping(other_observability.get("logging"))
        if logging_cfg.get("level") != other_logging.get("level"):
            diff.setdefault("observability.logging", {})["level"] = other_logging.get("level")
        retrieval = _as_mapping(self.payload.get("retrieval"))
        other_retrieval = _as_mapping(other.payload.get("retrieval"))
        fusion = _as_mapping(retrieval.get("fusion"))
        other_fusion = _as_mapping(other_retrieval.get("fusion"))
        if fusion != other_fusion:
            diff.setdefault("retrieval.fusion", {})["weights"] = other_fusion.get("weights")
        if self.feature_flags() != other.feature_flags():
            diff.setdefault("feature_flags", {})["values"] = cast(JSONValue, other.feature_flags())
        return diff

    def auth_secret(self) -> str:
        return self._auth_config().jwt_secret

    def auth_settings(self) -> AuthSettings:
        return self._auth_config().settings

    def catalog_vocabs(self) -> Mapping[str, JSONValue]:
        catalog = _as_mapping(self.payload.get("catalog"))
        return _as_mapping(catalog.get("vocabs"))

    def data(self) -> dict[str, JSONValue]:
        return dict(self.payload)

    def retrieval_runtime(self) -> Mapping[str, JSONValue]:
        return _as_mapping(self.payload.get("retrieval"))

    def pdf_pipeline(self) -> PdfPipelineSettings:
        pipelines = _as_mapping(self.payload.get("pipelines"))
        pdf = _as_mapping(pipelines.get("pdf"))
        ledger_raw = pdf.get("ledger_path")
        artifact_raw = pdf.get("artifact_dir")
        if not isinstance(ledger_raw, str) or not isinstance(artifact_raw, str):
            raise KeyError("pipelines.pdf ledger_path and artifact_dir must be configured")
        require_gpu_raw = pdf.get("require_gpu")
        require_gpu = True if require_gpu_raw is None else bool(require_gpu_raw)
        return PdfPipelineSettings(
            ledger_path=Path(ledger_raw),
            artifact_dir=Path(artifact_raw),
            require_gpu=require_gpu,
        )

    def entity_linking(self) -> Mapping[str, JSONValue]:
        return _as_mapping(self.payload.get("entity_linking"))

    def _auth_config(self) -> AuthConfig:
        apis = _as_mapping(self.payload.get("apis"))
        auth = _as_mapping(apis.get("auth"))
        jwt_secret = auth.get("jwt_secret")
        issuer = auth.get("issuer")
        audience = auth.get("audience")
        admin_scope = auth.get("admin_scope")
        if not isinstance(jwt_secret, str):
            raise KeyError("apis.auth.jwt_secret missing or invalid")
        if not isinstance(issuer, str):
            raise KeyError("apis.auth.issuer missing or invalid")
        if not isinstance(audience, str):
            raise KeyError("apis.auth.audience missing or invalid")
        if not isinstance(admin_scope, str):
            raise KeyError("apis.auth.admin_scope missing or invalid")
        settings = AuthSettings(issuer=issuer, audience=audience, admin_scope=admin_scope)
        return AuthConfig(jwt_secret=jwt_secret, settings=settings)


@dataclass(frozen=True)
class PolicyDocument:
    vocabs: Mapping[str, Mapping[str, JSONValue]]
    actions: Mapping[str, JSONValue]

    @classmethod
    def from_dict(cls, data: JSONMapping) -> "PolicyDocument":
        vocabs = data.get("vocabs")
        actions = data.get("actions")
        if not isinstance(vocabs, Mapping) or not isinstance(actions, Mapping):
            raise ValueError("policy.yaml must define vocabs and actions")
        normalized_vocabs: dict[str, Mapping[str, JSONValue]] = {}
        for vocab, config in vocabs.items():
            if not isinstance(vocab, str) or not isinstance(config, Mapping):
                raise ValueError("policy.yaml vocabs entries must be mappings")
            normalized_vocabs[vocab] = config
        return cls(vocabs=normalized_vocabs, actions=actions)


__all__ = [
    "AuthConfig",
    "AuthSettings",
    "Config",
    "PdfPipelineSettings",
    "PolicyDocument",
    "validate_constraints",
]
