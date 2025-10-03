"""Helpers for loading license configuration for ontology loaders."""

from __future__ import annotations

from pathlib import Path

from .pipeline import LicensePolicy


def load_license_policy(path: str | Path | None) -> LicensePolicy:
    """Load a license policy from a YAML file if present, otherwise permissive."""

    if path is None:
        return LicensePolicy.permissive()
    try:
        return LicensePolicy.from_file(path)
    except FileNotFoundError:
        return LicensePolicy.permissive()


__all__ = ["load_license_policy"]
