"""Licensing enforcement utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, MutableMapping

from Medical_KG.utils.yaml_loader import YamlLoaderError, load_yaml_mapping


class LicenseRegistryError(RuntimeError):
    """Raised when the license registry payload is invalid."""


@dataclass(frozen=True, slots=True)
class LicenseTier:
    """Feature gates, redaction policies, and limits associated with a tier."""

    name: str
    can_access: Mapping[str, bool]
    features: Mapping[str, bool]
    usage_limits: Mapping[str, int]
    redactions: Mapping[str, str]
    grace_period_days: int = 0

    def feature_enabled(self, feature: str) -> bool:
        return bool(self.features.get(feature, False))

    def redaction_for(self, vocab: str) -> str | None:
        return self.redactions.get(vocab.upper())


@dataclass(frozen=True, slots=True)
class LicenseEntry:
    vocab: str
    licensed: bool
    territory: str | None


class LicenseSession:
    """Per-user license view including overrides, usage, and expiration."""

    def __init__(
        self,
        registry: "LicenseRegistry",
        tier: str,
        *,
        expires_at: datetime | None = None,
    ) -> None:
        self._registry = registry
        self._tier_name = tier.lower()
        self._overrides: MutableMapping[str, bool] = {}
        self._usage: MutableMapping[str, int] = {}
        self._expires_at = expires_at

    @property
    def tier(self) -> LicenseTier:
        return self._registry.get_tier(self._tier_name)

    def set_override(self, feature: str, enabled: bool) -> None:
        self._overrides[feature] = enabled

    def upgrade(self, new_tier: str) -> None:
        self._tier_name = new_tier.lower()
        self._usage.clear()

    def downgrade(self, new_tier: str) -> None:
        self._tier_name = new_tier.lower()

    def check_expiration(self, *, now: datetime | None = None) -> None:
        tier = self.tier
        if self._expires_at is None:
            return
        current = now or datetime.now(timezone.utc)
        grace_end = self._expires_at + timedelta(days=tier.grace_period_days)
        if current <= grace_end:
            return
        raise PermissionError(
            f"License for tier {tier.name} expired at {self._expires_at.isoformat()}"
        )

    def enforce_feature(self, feature: str, *, now: datetime | None = None) -> None:
        self.check_expiration(now=now)
        override = self._overrides.get(feature)
        if override is not None:
            if not override:
                raise PermissionError(f"Feature {feature} disabled via override")
            return
        if not self.tier.feature_enabled(feature):
            raise PermissionError(f"Tier {self.tier.name} cannot access feature {feature}")

    def filter_label(self, vocab: str, label: str) -> str:
        tier = self.tier
        redaction = tier.redaction_for(vocab)
        if redaction:
            return redaction
        return self._registry.filter_labels(vocab, tier.name, label)

    def record_usage(self, metric: str, amount: int = 1) -> int:
        if amount < 0:
            raise ValueError("Usage amount must be non-negative")
        limit = self.tier.usage_limits.get(metric)
        current = self._usage.get(metric, 0) + amount
        if limit is not None and current > limit:
            raise PermissionError(f"Usage limit exceeded for {metric}")
        self._usage[metric] = current
        return current


class LicenseRegistry:
    """Loads and validates license entitlements from licenses.yml."""

    def __init__(
        self, entries: Mapping[str, LicenseEntry], tiers: Mapping[str, LicenseTier]
    ) -> None:
        self._entries = entries
        self._tiers = tiers

    @classmethod
    def from_yaml(cls, path: Path) -> "LicenseRegistry":
        try:
            data = load_yaml_mapping(path, description=path.name)
        except YamlLoaderError as exc:
            raise LicenseRegistryError(str(exc)) from exc
        vocabs_raw = data.get("vocabs", {})
        tier_defs = data.get("tiers", {})
        if not isinstance(vocabs_raw, Mapping):
            raise LicenseRegistryError(
                f"{path.name} field 'vocabs' must be a mapping"
            )
        if not isinstance(tier_defs, Mapping):
            raise LicenseRegistryError(
                f"{path.name} field 'tiers' must be a mapping"
            )
        entries = {
            vocab.upper(): LicenseEntry(
                vocab=vocab.upper(),
                licensed=bool(info.get("licensed")),
                territory=info.get("territory"),
            )
            for vocab, info in vocabs_raw.items()
        }

        def _mapping(section: Mapping[str, object] | None) -> Mapping[str, object]:
            if isinstance(section, Mapping):
                return {str(key): value for key, value in section.items()}
            return {}

        tiers: dict[str, LicenseTier] = {}
        for name, config in tier_defs.items():
            if not isinstance(config, Mapping):
                raise LicenseRegistryError(
                    f"{path.name} tier '{name}' must be a mapping"
                )
            can_access = {k.upper(): bool(v) for k, v in _mapping(config.get("vocabs")).items()}
            features = {k: bool(v) for k, v in _mapping(config.get("features")).items()}
            limits = {k: int(v) for k, v in _mapping(config.get("usage_limits")).items()}
            redactions: dict[str, str] = {}
            for vocab_name, value in _mapping(config.get("redactions")).items():
                value_str = str(value).strip()
                if value_str.startswith("'") and value_str.endswith("'"):
                    value_str = value_str[1:-1]
                if value_str.startswith('"') and value_str.endswith('"'):
                    value_str = value_str[1:-1]
                redactions[vocab_name.upper()] = value_str
            grace = int(config.get("grace_period_days", 0))
            tiers[name.lower()] = LicenseTier(
                name=name.lower(),
                can_access=can_access,
                features=features,
                usage_limits=limits,
                redactions=redactions,
                grace_period_days=grace,
            )
        return cls(entries, tiers)

    def available_tiers(self) -> tuple[str, ...]:
        return tuple(sorted(self._tiers))

    def get_tier(self, name: str) -> LicenseTier:
        try:
            return self._tiers[name.lower()]
        except KeyError as exc:
            raise KeyError(f"Unknown license tier {name}") from exc

    def create_session(self, tier: str, *, expires_at: datetime | None = None) -> LicenseSession:
        self.get_tier(tier)
        return LicenseSession(self, tier, expires_at=expires_at)

    def require(self, vocab: str) -> None:
        entry = self._entries.get(vocab.upper())
        if entry is None or not entry.licensed:
            raise PermissionError(f"Vocabulary {vocab} is not licensed")

    def filter_labels(self, vocab: str, tier: str, label: str) -> str:
        entry = self._entries.get(vocab.upper())
        tier_entry = self._tiers.get(tier.lower())
        if entry is None:
            return "[unavailable]"
        if not entry.licensed:
            return "[license required]"
        if tier_entry and not tier_entry.can_access.get(vocab.upper(), True):
            return f"[{tier} tier cannot access {vocab}]"
        return label


__all__ = [
    "LicenseRegistry",
    "LicenseRegistryError",
    "LicenseTier",
    "LicenseSession",
]
