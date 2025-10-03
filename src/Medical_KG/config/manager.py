"""Configuration loading, validation, and hot-reload support."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional
from typing import TYPE_CHECKING

import yaml

from .models import Config, PolicyDocument, validate_constraints

if TYPE_CHECKING:
    from prometheus_client import Gauge
else:  # pragma: no cover - optional dependency
    try:
        from prometheus_client import Gauge
    except ModuleNotFoundError:

        class Gauge:
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

            def labels(self, **_: Any) -> "Gauge":
                return self

            def set(self, *_: Any, **__: Any) -> None:
                return None

            def clear(self) -> None:
                return None


CONFIG_INFO = Gauge("config_info", "Current configuration metadata", ["version", "hash"])
FEATURE_FLAG = Gauge("feature_flag", "Feature flag states", ["name"])

ENV_SIMPLE_PATHS: Mapping[str, str] = {
    "VLLM_API_BASE": "embeddings.vllm_api_base",
    "RETRIEVAL_FUSION_WEIGHTS": "retrieval.fusion.weights",
    "LOG_LEVEL": "observability.logging.level",
}

PLACEHOLDER_PATTERN = re.compile(r"\${([A-Z0-9_]+)(?::([^}]+))?}")


class ConfigError(RuntimeError):
    """Raised when configuration validation fails."""


@dataclass
class ConfigVersion:
    raw: str
    hash: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ConfigVersion":
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        version = f"{datetime.now(timezone.utc).isoformat()}+{digest[:12]}"
        return cls(raw=version, hash=digest)


class SecretResolver:
    """Resolves ${VAR} placeholders using environment variables or provided mapping."""

    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self._env = dict(env or os.environ)

    def resolve(self, key: str, default: Optional[str] = None) -> str:
        if key in self._env:
            return self._env[key]
        if default is not None:
            return default
        raise ConfigError(f"Missing required secret: {key}")


class ConfigValidator:
    """Minimal JSON Schema validator supporting the subset used by config.schema.json."""

    def __init__(self, schema_path: Path):
        with schema_path.open("r", encoding="utf-8") as handle:
            self._schema = json.load(handle)
        self._definitions = self._schema.get("definitions", {})

    def validate(self, payload: Mapping[str, Any]) -> None:
        errors: list[str] = []
        self._validate_schema(payload, self._schema, [], errors)
        if errors:
            raise ConfigError("; ".join(errors))

    def _resolve(self, schema: Mapping[str, Any]) -> Mapping[str, Any]:
        if "$ref" in schema:
            ref = schema["$ref"]
            if not ref.startswith("#/definitions/"):
                raise ConfigError(f"Unsupported $ref: {ref}")
            key = ref.split("/")[-1]
            return self._definitions[key]
        return schema

    def _validate_schema(
        self,
        value: Any,
        schema: Mapping[str, Any],
        path: list[str],
        errors: list[str],
    ) -> None:
        schema = self._resolve(schema)
        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            if value is None and "null" in schema_type:
                return
            schema_type = [t for t in schema_type if t != "null"]
            schema_type = schema_type[0] if schema_type else None
        if schema_type == "object":
            if not isinstance(value, MutableMapping):
                errors.append(self._format_path(path, "expected object"))
                return
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            for key in required:
                if key not in value:
                    errors.append(self._format_path(path + [key], "missing required property"))
            for key, val in value.items():
                subschema = properties.get(key)
                if subschema is not None:
                    self._validate_schema(val, subschema, path + [key], errors)
                elif not schema.get("additionalProperties", True):
                    errors.append(self._format_path(path + [key], "unexpected property"))
        elif schema_type == "array":
            if not isinstance(value, list):
                errors.append(self._format_path(path, "expected array"))
                return
            item_schema = schema.get("items")
            for index, item in enumerate(value):
                if item_schema is not None:
                    self._validate_schema(item, item_schema, path + [str(index)], errors)
        elif schema_type == "string":
            if not isinstance(value, str):
                errors.append(self._format_path(path, "expected string"))
                return
            enum = schema.get("enum")
            if enum and value not in enum:
                errors.append(self._format_path(path, f"must be one of {enum}"))
        elif schema_type == "integer":
            if not isinstance(value, int):
                errors.append(self._format_path(path, "expected integer"))
                return
            self._validate_numeric_bounds(value, schema, path, errors)
        elif schema_type == "number":
            if not isinstance(value, (int, float)):
                errors.append(self._format_path(path, "expected number"))
                return
            self._validate_numeric_bounds(float(value), schema, path, errors)
        elif schema_type == "boolean":
            if not isinstance(value, bool):
                errors.append(self._format_path(path, "expected boolean"))
        else:
            # fallback: still walk subschemas if present
            if isinstance(value, MutableMapping) and "properties" in schema:
                self._validate_schema(value, {"type": "object", **schema}, path, errors)

    def _validate_numeric_bounds(
        self, value: float, schema: Mapping[str, Any], path: list[str], errors: list[str]
    ) -> None:
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(self._format_path(path, f"must be >= {minimum}"))
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            errors.append(self._format_path(path, f"must be <= {maximum}"))

    def _format_path(self, path: list[str], message: str) -> str:
        location = "/".join(path) if path else "<root>"
        return f"{location}: {message}"


class ConfigManager:
    """Central coordinator for runtime configuration."""

    def __init__(
        self,
        base_path: Optional[Path] = None,
        env: Optional[str] = None,
        secret_resolver: Optional[SecretResolver] = None,
    ) -> None:
        self.base_path = base_path or Path(__file__).resolve().parent
        self.env = (env or os.getenv("CONFIG_ENV", "dev")).lower()
        self.secret_resolver = secret_resolver or SecretResolver()
        self.validator = ConfigValidator(self.base_path / "config.schema.json")
        self.policy = self._load_policy()
        self._config: Config
        self._version: ConfigVersion
        self.reload()

    @property
    def config(self) -> Config:
        return self._config

    @property
    def version(self) -> ConfigVersion:
        return self._version

    def _load_policy(self) -> PolicyDocument:
        policy_path = self.base_path / "policy.yaml"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy_data = yaml.safe_load(handle) or {}
        try:
            return PolicyDocument.from_dict(policy_data)
        except ValueError as exc:
            raise ConfigError(f"policy.yaml invalid: {exc}") from exc

    def reload(self) -> None:
        payload = self._load_configuration_payload()
        resolved = self._resolve_placeholders(payload)
        self.validator.validate(resolved)
        try:
            validate_constraints(resolved)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        config = Config(dict(resolved))
        self._validate_licensing(config)
        version = ConfigVersion.from_payload(resolved)
        if hasattr(self, "_config"):
            breaking = self._config.breaking_changes(config)
            if breaking:
                raise ConfigError(
                    "Breaking change requires restart: " + ", ".join(sorted(breaking))
                )
        self._config = config
        self._version = version
        self._emit_metrics()

    def raw_payload(self) -> Dict[str, Any]:
        """Return the merged configuration payload prior to validation."""
        return self._load_configuration_payload()

    def _load_configuration_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = self._load_yaml(self.base_path / "config.yaml")
        env_specific = self.base_path / f"config-{self.env}.yaml"
        if env_specific.exists():
            payload = self._deep_merge(payload, self._load_yaml(env_specific))
        override_path = self.base_path / "config-override.yaml"
        if override_path.exists():
            payload = self._deep_merge(payload, self._load_yaml(override_path))
        payload = self._apply_env_overrides(payload)
        return payload

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, MutableMapping):
            raise ConfigError(f"{path.name} must contain a mapping at the root")
        return dict(data)

    def _deep_merge(
        self, base: MutableMapping[str, Any], overlay: Mapping[str, Any]
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(base)
        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], MutableMapping)
                and isinstance(value, Mapping)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(payload)
        # handle explicit mappings
        for env_name, dotted_path in ENV_SIMPLE_PATHS.items():
            if env_name in os.environ:
                self._set_dotted_key(result, dotted_path, self._parse_env_value(os.environ[env_name]))
        # handle MEDCFG__ style overrides
        for env_name, value in os.environ.items():
            if not env_name.startswith("MEDCFG__"):
                continue
            dotted = env_name[len("MEDCFG__") :].lower().replace("__", ".")
            self._set_dotted_key(result, dotted, self._parse_env_value(value))
        return result

    def _parse_env_value(self, raw: str) -> Any:
        raw = raw.strip()
        if raw.lower() in {"true", "false"}:
            return raw.lower() == "true"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    def _set_dotted_key(self, payload: Dict[str, Any], dotted_path: str, value: Any) -> None:
        parts = dotted_path.split(".")
        cursor: MutableMapping[str, Any] = payload
        for part in parts[:-1]:
            next_value = cursor.get(part)
            if not isinstance(next_value, MutableMapping):
                next_value = {}
                cursor[part] = next_value
            cursor = next_value
        cursor[parts[-1]] = value

    def _resolve_placeholders(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        def _resolve(value: Any) -> Any:
            if isinstance(value, str):
                return self._resolve_string(value)
            if isinstance(value, Mapping):
                return {key: _resolve(val) for key, val in value.items()}
            if isinstance(value, list):
                return [_resolve(item) for item in value]
            return value

        return {key: _resolve(val) for key, val in payload.items()}

    def _resolve_string(self, value: str) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            default = match.group(2)
            return self.secret_resolver.resolve(key, default)

        return PLACEHOLDER_PATTERN.sub(replace, value)

    def _validate_licensing(self, config: Config) -> None:
        for vocab_name, vocab_config in config.catalog_vocabs().items():
            policy_entry = self.policy.vocabs.get(vocab_name.upper())
            requires_license = bool(vocab_config.get("requires_license"))
            enabled = bool(vocab_config.get("enabled"))
            if (
                enabled
                and requires_license
                and (policy_entry is None or not policy_entry.get("licensed"))
            ):
                raise ConfigError(
                    f"{vocab_name} requires affiliate license but policy.yaml marks it unlicensed"
                )

    def _emit_metrics(self) -> None:
        CONFIG_INFO.clear()
        CONFIG_INFO.labels(version=self._version.raw, hash=self._version.hash).set(1)
        FEATURE_FLAG.clear()
        for name, enabled in self._config.feature_flags().items():
            FEATURE_FLAG.labels(name=name).set(1 if enabled else 0)

    def validate_jwt(self, token: str) -> Mapping[str, Any]:
        secret = self._config.auth_secret()
        claims = self._decode_jwt(token, secret)
        issuer = claims.get("iss")
        audience = claims.get("aud")
        expected = self._config.auth_settings()
        if issuer != expected["issuer"]:
            raise ConfigError("Invalid token issuer")
        if audience != expected["audience"]:
            raise ConfigError("Invalid token audience")
        scope_field = claims.get("scope") or claims.get("scopes")
        scopes: set[str]
        if isinstance(scope_field, str):
            scopes = set(scope_field.split())
        elif isinstance(scope_field, list):
            scopes = set(scope_field)
        else:
            scopes = set()
        if expected["admin_scope"] not in scopes:
            raise ConfigError("Admin scope missing from token")
        return claims

    def _decode_jwt(self, token: str, secret: str) -> Dict[str, Any]:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:  # pragma: no cover - defensive
            raise ConfigError("Invalid admin token") from exc
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_signature = _b64url_encode(
            hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_signature, signature_b64):
            raise ConfigError("Invalid admin token")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            raise ConfigError("Unsupported JWT algorithm")
        payload = json.loads(_b64url_decode(payload_b64))
        return payload


def mask_secrets(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of *data* with secret fields masked."""

    def _mask(value: Any, key: Optional[str] = None) -> Any:
        if isinstance(value, Mapping):
            return {child_key: _mask(child_val, child_key) for child_key, child_val in value.items()}
        if isinstance(value, list):
            return [_mask(item, key) for item in value]
        if isinstance(key, str) and any(
            key.lower().endswith(suffix) for suffix in ("_key", "_secret", "_token", "password")
        ):
            return "***"
        if isinstance(value, str) and PLACEHOLDER_PATTERN.search(value):
            return "***"
        return value

    return {key: _mask(val, key) for key, val in data.items()}


__all__ = ["ConfigManager", "ConfigError", "mask_secrets", "ConfigValidator", "SecretResolver"]


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")
