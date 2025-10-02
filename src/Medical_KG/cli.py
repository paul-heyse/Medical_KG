"""Simple command-line interface for configuration management."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from Medical_KG.config.manager import ConfigError, ConfigManager, ConfigValidator, mask_secrets
from Medical_KG.security.licenses import LicenseRegistry


def _load_manager(config_dir: Optional[Path]) -> ConfigManager:
    base_path = config_dir or Path(__file__).resolve().parent / "config"
    return ConfigManager(base_path=base_path)


def _command_validate(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
        payload = manager.raw_payload()
        ConfigValidator(manager.base_path / "config.schema.json").validate(payload)
        _ = manager.config
    except ConfigError as exc:
        print(f"Configuration invalid: {exc}")
        return 1
    message = "Config valid (strict)" if args.strict else "Config valid"
    print(message)
    return 0


def _command_show(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
        payload = manager.raw_payload()
        if args.mask:
            payload = mask_secrets(payload)
    except ConfigError as exc:
        print(f"Unable to load configuration: {exc}")
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _command_policy(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
        policy = manager.policy
    except ConfigError as exc:
        print(f"Unable to load policy: {exc}")
        return 1
    for vocab, config in policy.vocabs.items():
        territory = config.territory or "-"
        licensed = "licensed" if config.licensed else "unlicensed"
        print(f"{vocab}: {licensed} ({territory})")
    return 0


def _command_licensing_validate(args: argparse.Namespace) -> int:
    path = args.licenses
    try:
        LicenseRegistry.from_yaml(path)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Licenses invalid: {exc}")
        return 1
    print("Licenses valid")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="med", description="Medical KG command-line tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    validate = config_subparsers.add_parser("validate", help="Validate configuration files")
    validate.add_argument("--strict", action="store_true", help="Fail on any warning")
    validate.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    validate.set_defaults(func=_command_validate)

    show = config_subparsers.add_parser("show", help="Print effective configuration")
    show.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    show.add_argument("--mask", action="store_true", default=True)
    show.add_argument("--no-mask", dest="mask", action="store_false")
    show.set_defaults(func=_command_show)

    policy = config_subparsers.add_parser("policy", help="Display licensing policy")
    policy.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    policy.set_defaults(func=_command_policy)

    licensing = subparsers.add_parser("licensing", help="Licensing commands")
    licensing_subparsers = licensing.add_subparsers(dest="licensing_command", required=True)
    licensing_validate = licensing_subparsers.add_parser("validate", help="Validate licenses.yml")
    licensing_validate.add_argument("--licenses", type=Path, default=Path("licenses.yml"))
    licensing_validate.set_defaults(func=_command_licensing_validate)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
