"""Configuration loader and validator with strict typing support."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, cast

import yaml
from jsonschema import FormatChecker, ValidationError
from jsonschema.validators import validator_for
from packaging.version import InvalidVersion, Version

from Medical_KG.compat.prometheus import Gauge, GaugeLike
from Medical_KG.types import JSONMapping, JSONObject, JSONValue, MutableJSONMapping

from .models import AuthSettings, Config, PolicyDocument, validate_constraints

CONFIG_INFO: GaugeLike = Gauge("config_info", "Current configuration metadata", ["version", "hash"])
FEATURE_FLAG: GaugeLike = Gauge("feature_flag", "Feature flag states", ["name"])

ENV_SIMPLE_PATHS: Mapping[str, str] = {
    "VLLM_API_BASE": "embeddings.vllm_api_base",
    "RETRIEVAL_FUSION_WEIGHTS": "retrieval.fusion.weights",
    "LOG_LEVEL": "observability.logging.level",
}

PLACEHOLDER_PATTERN = re.compile(r"\${([A-Z0-9_]+)(?::([^}]+))?}")
SCHEMA_REF_VERSION_PATTERN = re.compile(r"v(?P<version>\d+\.\d+\.\d+)")
REQUIRED_MESSAGE_PATTERN = re.compile(r"'(?P<field>[^']+)' is a required property")
SIMPLE_DURATION_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")

LOGGER = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = "1.0.0"
ALLOW_OLD_SCHEMA_ENV = "MEDCFG_ALLOW_OLD_SCHEMA"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class ConfigError(RuntimeError):
    """Raised when configuration validation fails."""


@dataclass
class ConfigVersion:
    raw: str
    hash: str

    @classmethod
    def from_payload(cls, payload: JSONMapping) -> "ConfigVersion":
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        version = f"{datetime.now(timezone.utc).isoformat()}+{digest[:12]}"
        return cls(raw=version, hash=digest)


class SecretResolver:
    """Resolves ${VAR} placeholders using environment variables or provided mapping."""

    def __init__(self, env: Mapping[str, str] | None = None):
        self._env = dict(env or os.environ)

    def resolve(self, key: str, default: str | None = None) -> str:
        if key in self._env:
            return self._env[key]
        if default is not None:
            return default
        raise ConfigError(f"Missing required secret: {key}")


@lru_cache(maxsize=1)
def _adapter_names() -> frozenset[str]:
    from Medical_KG.ingestion.registry import available_sources

    return frozenset(available_sources())


def _build_format_checker() -> FormatChecker:
    checker = FormatChecker()

    @checker.checks("duration")
    def _validate_duration(value: Any) -> bool:  # pragma: no cover - jsonschema handles errors
        return isinstance(value, str) and bool(SIMPLE_DURATION_PATTERN.fullmatch(value))

    @checker.checks("adapter_name")
    def _validate_adapter_name(value: Any) -> bool:  # pragma: no cover - jsonschema handles errors
        return isinstance(value, str) and value in _adapter_names()

    return checker


def _pointer_from_path(path: Iterable[Any]) -> str:
    parts = [str(part) for part in path]
    if not parts:
        return "<root>"
    return "/" + "/".join(parts)


def _stringify_instance(value: JSONValue) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def _expected_description(error: ValidationError) -> str | None:
    validator = error.validator
    data = error.validator_value
    if validator == "type":
        if isinstance(data, list):
            return " or ".join(str(item) for item in data)
        return str(data)
    if validator == "enum" and isinstance(data, Iterable):
        return "one of " + ", ".join(str(item) for item in data)
    if validator in {"minimum", "exclusiveMinimum"}:
        comparator = ">=" if validator == "minimum" else ">"
        return f"{comparator} {data}"
    if validator in {"maximum", "exclusiveMaximum"}:
        comparator = "<=" if validator == "maximum" else "<"
        return f"{comparator} {data}"
    if validator in {"minItems", "maxItems"}:
        comparator = ">=" if validator == "minItems" else "<="
        return f"array length {comparator} {data}"
    if validator == "required":
        match = REQUIRED_MESSAGE_PATTERN.search(error.message)
        if match:
            return f"required property '{match.group('field')}'"
    if validator == "additionalProperties":
        return "only declared properties"
    if validator == "format" and isinstance(error.schema, Mapping):
        fmt = error.schema.get("format")
        if isinstance(fmt, str):
            return f"format '{fmt}'"
    return None


def _remediation_hint(error: ValidationError) -> str | None:
    validator = error.validator
    if validator == "enum" and isinstance(error.validator_value, Iterable):
        options = ", ".join(str(item) for item in error.validator_value)
        return f"Choose one of: {options}."
    if validator == "type":
        expected = error.validator_value
        if isinstance(expected, list):
            expected = ", ".join(str(item) for item in expected)
        return f"Provide a value of type {expected}."
    if validator in {"minimum", "exclusiveMinimum"}:
        return f"Increase the value to at least {error.validator_value}."
    if validator in {"maximum", "exclusiveMaximum"}:
        return f"Reduce the value to at most {error.validator_value}."
    if validator == "required":
        match = REQUIRED_MESSAGE_PATTERN.search(error.message)
        if match:
            return f"Add the missing '{match.group('field')}' property."
    if validator == "additionalProperties":
        return "Remove unexpected properties or update the schema."
    if validator == "format" and isinstance(error.schema, Mapping):
        fmt = error.schema.get("format")
        if fmt == "duration":
            return "Use durations like '5m', '15m', or '1h'."
        if fmt == "adapter_name":
            known = ", ".join(sorted(_adapter_names()))
            return f"Select a registered adapter ({known})."
    return None


def _extract_declared_version(payload: Mapping[str, JSONValue]) -> str | None:
    version_field = payload.get("$schema_version")
    if isinstance(version_field, str):
        return version_field
    schema_ref = payload.get("$schema")
    if isinstance(schema_ref, str):
        match = SCHEMA_REF_VERSION_PATTERN.search(schema_ref)
        if match:
            return match.group("version")
    return None


class ConfigSchemaValidator:
    """Wrap jsonschema validation with custom formats and error reporting."""

    def __init__(
        self,
        schema_path: Path,
        *,
        format_checker: FormatChecker | None = None,
        allow_older: bool | None = None,
    ):
        self._schema_path = schema_path
        with schema_path.open("r", encoding="utf-8") as handle:
            raw_schema = json.load(handle)
        if not isinstance(raw_schema, MutableMapping):
            raise ConfigError("config.schema.json must contain an object at the root")
        schema = cast(JSONMapping, raw_schema)
        version = schema.get("version")
        if not isinstance(version, str):
            raise ConfigError("config.schema.json must declare a string 'version'")
        self.version = version
        if self.version != CURRENT_SCHEMA_VERSION:
            LOGGER.warning(
                "Schema version %s does not match expected %s",
                self.version,
                CURRENT_SCHEMA_VERSION,
            )
        self._schema = schema
        self._format_checker = format_checker or _build_format_checker()
        try:
            self._supported_version = Version(self.version)
        except InvalidVersion as exc:
            raise ConfigError(
                "config.schema.json 'version' must follow semantic versioning"
            ) from exc
        self._allow_older = allow_older if allow_older is not None else _env_flag(ALLOW_OLD_SCHEMA_ENV, True)
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        self._validator = validator_cls(schema, format_checker=self._format_checker)

    def validate(self, payload: JSONMapping, *, source: str = "configuration") -> None:
        declared_version = _extract_declared_version(payload)
        if declared_version is None:
            LOGGER.warning(
                "%s does not declare a $schema version. Add \"$schema\": \"https://medical-kg.dev/schemas/config/v%s.json\".",
                source,
                self.version,
            )
        else:
            try:
                declared = Version(declared_version)
            except InvalidVersion as exc:
                raise ConfigError(
                    f"{source} declares schema version {declared_version!r} which is not a valid version string."
                ) from exc
            if declared > self._supported_version:
                raise ConfigError(
                    f"{source} declares schema version {declared_version} newer than supported {self.version}. "
                    "Review docs/configuration.md for migration steps or upgrade the runtime."
                )
            if declared < self._supported_version:
                message = (
                    f"{source} declares schema version {declared_version} older than supported {self.version}. "
                    "Review docs/configuration.md for migration guidance."
                )
                if self._allow_older:
                    LOGGER.warning("%s Set %s=0 to fail on older schemas.", message, ALLOW_OLD_SCHEMA_ENV)
                else:
                    raise ConfigError(message + f" Set {ALLOW_OLD_SCHEMA_ENV}=1 to permit older schemas.")

        errors = sorted(
            self._validator.iter_errors(payload), key=lambda err: tuple(str(p) for p in err.absolute_path)
        )
        if not errors:
            return

        messages = [
            self._format_error(error, source)
            for error in errors
        ]
        raise ConfigError("Configuration validation failed:\n" + "\n\n".join(messages))

    def _format_error(self, error: ValidationError, source: str) -> str:
        pointer = _pointer_from_path(error.absolute_path)
        value_repr = _stringify_instance(cast(JSONValue, error.instance))
        expected = _expected_description(error)
        hint = _remediation_hint(error)
        lines = [
            f"{source} -> {pointer}",
            f"  Problem: {error.message}",
            f"  Value: {value_repr}",
        ]
        if expected:
            lines.append(f"  Expected: {expected}")
        if hint:
            lines.append(f"  Hint: {hint}")
        return "\n".join(lines)


class ConfigManager:
    """Central coordinator for runtime configuration."""

    def __init__(
        self,
        base_path: Path | None = None,
        env: str | None = None,
        secret_resolver: SecretResolver | None = None,
        allow_older_schema: bool | None = None,
    ) -> None:
        self.base_path = base_path or Path(__file__).resolve().parent
        env_value = env if env is not None else os.getenv("CONFIG_ENV", "dev")
        self.env = env_value.lower()
        self.secret_resolver = secret_resolver or SecretResolver()
        self.validator = ConfigSchemaValidator(
            self.base_path / "config.schema.json",
            allow_older=allow_older_schema,
        )
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
        if not isinstance(policy_data, MutableMapping):
            raise ConfigError("policy.yaml must contain a mapping at the root")
        try:
            normalized = dict(cast(MutableJSONMapping, policy_data))
            return PolicyDocument.from_dict(normalized)
        except ValueError as exc:
            raise ConfigError(f"policy.yaml invalid: {exc}") from exc

    def reload(self) -> None:
        payload = self._load_configuration_payload()
        resolved = self._resolve_placeholders(payload)
        self.validator.validate(resolved, source="configuration")
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

    def raw_payload(self) -> JSONObject:
        """Return the merged configuration payload prior to validation."""
        return self._load_configuration_payload()

    def _load_configuration_payload(self) -> JSONObject:
        payload = self._load_yaml(self.base_path / "config.yaml")
        env_specific = self.base_path / f"config-{self.env}.yaml"
        if env_specific.exists():
            payload = self._deep_merge(payload, self._load_yaml(env_specific))
        override_path = self.base_path / "config-override.yaml"
        if override_path.exists():
            payload = self._deep_merge(payload, self._load_yaml(override_path))
        return self._apply_env_overrides(payload)

    def _load_yaml(self, path: Path) -> JSONObject:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, MutableMapping):
            raise ConfigError(f"{path.name} must contain a mapping at the root")
        return dict(cast(MutableJSONMapping, data))

    def _deep_merge(self, base: MutableJSONMapping, overlay: JSONMapping) -> JSONObject:
        result: JSONObject = dict(base)
        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], MutableMapping)
                and isinstance(value, Mapping)
            ):
                result[key] = self._deep_merge(cast(MutableJSONMapping, result[key]), value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, payload: JSONObject) -> JSONObject:
        result: JSONObject = dict(payload)
        for env_name, dotted_path in ENV_SIMPLE_PATHS.items():
            if env_name in os.environ:
                parsed = self._parse_env_value(os.environ[env_name])
                self._set_dotted_key(result, dotted_path, parsed)
        for env_name, value in os.environ.items():
            if not env_name.startswith("MEDCFG__"):
                continue
            dotted = env_name[len("MEDCFG__") :].lower().replace("__", ".")
            self._set_dotted_key(result, dotted, self._parse_env_value(value))
        return result

    def _parse_env_value(self, raw: str) -> JSONValue:
        raw = raw.strip()
        lowered = raw.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            loaded = None
        else:
            return cast(JSONValue, loaded)
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    def _set_dotted_key(
        self, payload: MutableJSONMapping, dotted_path: str, value: JSONValue
    ) -> None:
        parts = dotted_path.split(".")
        cursor: MutableJSONMapping = payload
        for part in parts[:-1]:
            next_value = cursor.get(part)
            if not isinstance(next_value, MutableMapping):
                next_value = {}
                cursor[part] = next_value
            cursor = cast(MutableMapping[str, Any], next_value)
        cursor[parts[-1]] = value

    def _resolve_placeholders(self, payload: JSONMapping) -> JSONObject:
        def _resolve(value: JSONValue) -> JSONValue:
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
            vocab_mapping = vocab_config if isinstance(vocab_config, Mapping) else {}
            policy_entry = self.policy.vocabs.get(vocab_name.upper())
            requires_license = bool(vocab_mapping.get("requires_license"))
            enabled = bool(vocab_mapping.get("enabled"))
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

    def validate_jwt(self, token: str) -> Mapping[str, JSONValue]:
        secret = self._config.auth_secret()
        claims = self._decode_jwt(token, secret)
        issuer = claims.get("iss")
        audience = claims.get("aud")
        expected: AuthSettings = self._config.auth_settings()
        if issuer != expected.issuer:
            raise ConfigError("Invalid token issuer")
        if audience != expected.audience:
            raise ConfigError("Invalid token audience")
        scope_field = claims.get("scope") or claims.get("scopes")
        scopes: set[str]
        if isinstance(scope_field, str):
            scopes = set(scope_field.split())
        elif isinstance(scope_field, list):
            scopes = {str(item) for item in scope_field}
        else:
            scopes = set()
        if expected.admin_scope not in scopes:
            raise ConfigError("Admin scope missing from token")
        return cast(Mapping[str, JSONValue], claims)

    def _decode_jwt(self, token: str, secret: str) -> JSONObject:
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
        if not isinstance(payload, MutableMapping):
            raise ConfigError("JWT payload must be an object")
        return cast(JSONObject, payload)


def mask_secrets(data: JSONMapping) -> JSONObject:
    """Return a deep copy of *data* with secret fields masked."""

    def _mask(value: JSONValue, key: str | None = None) -> JSONValue:
        if isinstance(value, Mapping):
            return {
                child_key: _mask(child_val, child_key) for child_key, child_val in value.items()
            }
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


__all__ = [
    "ConfigManager",
    "ConfigError",
    "ConfigSchemaValidator",
    "mask_secrets",
    "SecretResolver",
]


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")
