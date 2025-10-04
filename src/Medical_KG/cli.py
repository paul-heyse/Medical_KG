"""Simple command-line interface for configuration management."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from pathlib import Path
from types import TracebackType
from typing import Any, Iterable, Protocol, cast

from Medical_KG.config.manager import ConfigError, ConfigManager, ConfigValidator, mask_secrets
from Medical_KG.config.models import PdfPipelineSettings
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.pdf import (
    GpuNotAvailableError,
    MinerUConfig,
    MinerURunner,
    PdfDocument,
    PdfPipeline,
    ensure_gpu,
)
from Medical_KG.security.licenses import LicenseRegistry


class HttpxResponse(Protocol):
    content: bytes

    def raise_for_status(self) -> None: ...


class HttpxClient(Protocol):
    def __enter__(self) -> "HttpxClient": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def get(self, url: str, *, follow_redirects: bool) -> HttpxResponse: ...


class HttpxModule(Protocol):
    HTTPError: type[Exception]

    def Client(self, *, timeout: float) -> HttpxClient: ...


def _require_httpx() -> HttpxModule:
    try:
        module = importlib.import_module("httpx")
    except Exception as exc:  # pragma: no cover - dependency check
        raise RuntimeError("httpx is required for CLI operations") from exc
    return cast(HttpxModule, module)


_HTTPX = _require_httpx()
HTTPError = _HTTPX.HTTPError


def _load_manager(config_dir: Path | None) -> ConfigManager:
    base_path = config_dir or Path(__file__).resolve().parent / "config"
    return ConfigManager(base_path=base_path)


def _build_pipeline(manager: ConfigManager) -> PdfPipeline:
    pdf_config: PdfPipelineSettings = manager.config.pdf_pipeline()
    ledger_path = pdf_config.ledger_path.expanduser()
    artifact_dir = pdf_config.artifact_dir.expanduser()
    mineru = MinerURunner(MinerUConfig(output_dir=artifact_dir))
    ledger = IngestionLedger(ledger_path)
    return PdfPipeline(ledger=ledger, mineru=mineru)


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
        territory = config.get("territory") or "-"
        licensed = "licensed" if config.get("licensed", False) else "unlicensed"
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


def _command_ingest_pdf(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
    except ConfigError as exc:
        print(f"Unable to load configuration: {exc}")
        return 1
    pipeline_config = manager.config.pdf_pipeline()
    downloads_dir = pipeline_config.artifact_dir.expanduser() / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    destination = downloads_dir / f"{args.doc_key}.pdf"
    try:
        with _HTTPX.Client(timeout=30.0) as client:
            response = client.get(args.uri, follow_redirects=True)
            response.raise_for_status()
    except HTTPError as exc:
        print(f"Failed to download PDF: {exc}", file=sys.stderr)
        return 1
    destination.write_bytes(response.content)
    ledger = IngestionLedger(pipeline_config.ledger_path.expanduser())
    ledger.record(
        args.doc_key,
        "pdf_downloaded",
        {"uri": args.uri, "local_path": str(destination)},
    )
    print(f"Stored {args.doc_key} at {destination}")
    return 0


def _command_mineru_run(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
    except ConfigError as exc:
        print(f"Unable to load configuration: {exc}")
        return 1
    pipeline = _build_pipeline(manager)
    pdf_config = manager.config.pdf_pipeline()
    ledger = IngestionLedger(pdf_config.ledger_path.expanduser())
    entries = ledger.entries(state="pdf_downloaded")
    if args.doc_key:
        entries = [entry for entry in entries if entry.doc_id == args.doc_key]
    if not entries:
        print("No PDFs ready for MinerU")
        return 0
    exit_code = 0
    for entry in entries:
        local_path = entry.metadata.get("local_path")
        if not local_path:
            print(f"Skipping {entry.doc_id}: missing local_path", file=sys.stderr)
            continue
        document = PdfDocument(
            doc_key=entry.doc_id,
            uri=str(entry.metadata.get("uri", "")),
            local_path=Path(local_path),
        )
        try:
            metadata = pipeline.process(document)
            print(f"MinerU completed for {entry.doc_id}: {metadata['mineru_artifacts']}")
        except GpuNotAvailableError as exc:
            print(str(exc), file=sys.stderr)
            exit_code = 99 if args.fail_if_no_gpu else exit_code or 0
            if args.fail_if_no_gpu:
                return 99
            break
        except RuntimeError as exc:
            ledger.record(entry.doc_id, "mineru_failed", {"error": str(exc)})
            print(f"MinerU failed for {entry.doc_id}: {exc}", file=sys.stderr)
    return exit_code


def _command_postpdf(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
    except ConfigError as exc:
        print(f"Unable to load configuration: {exc}")
        return 1
    pdf_config = manager.config.pdf_pipeline()
    require_gpu = pdf_config.require_gpu
    try:
        ensure_gpu(require_flag=require_gpu)
    except GpuNotAvailableError as exc:
        print(str(exc), file=sys.stderr)
        return 99
    ledger = IngestionLedger(pdf_config.ledger_path.expanduser())
    entries = list(ledger.entries(state="pdf_ir_ready"))
    for entry in entries:
        ledger.record(entry.doc_id, "postpdf_started", {"steps": args.steps})
    print(f"Triggered downstream processing for {len(entries)} document(s)")
    return 0


LEGACY_FLAG_ALIASES: dict[str, str] = {
    "--batch": "--batch",
    "--batch-file": "--batch",
    "--continue-from-ledger": "--resume",
    "--ledger": "--ledger",
    "--max-records": "--limit",
    "--format": "--output",
    "--quiet": "--quiet",
    "--verbose": "--verbose",
    "--auto": "--auto",
    "--resume": "--resume",
    "--chunk-size": "--chunk-size",
    "--skip-validation": "--skip-validation",
    "--strict-validation": "--strict-validation",
    "--fail-fast": "--fail-fast",
}

SHORT_FLAG_ALIASES: dict[str, str] = {
    "-b": "--batch",
    "-o": "--output",
    "-n": "--limit",
    "-r": "--resume",
    "-q": "--quiet",
    "-v": "--verbose",
}

BOOLEAN_FLAGS = {
    "--resume",
    "--auto",
    "--quiet",
    "--verbose",
    "--fail-fast",
    "--skip-validation",
    "--strict-validation",
}


def _translate_legacy_args(argv: list[str]) -> tuple[list[str], bool]:
    tokens = list(argv)
    if not tokens:
        return [], False
    if tokens == ["--help"] or tokens == ["-h"]:
        return ["--help"], False
    adapter_from_source: str | None = None
    translated: list[str] = []
    used_legacy = False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"--help", "-h"}:
            return ["--help"], used_legacy
        if token == "--source":
            used_legacy = True
            if index + 1 < len(tokens):
                adapter_from_source = tokens[index + 1]
                index += 2
            else:
                index += 1
            continue
        if token == "--ids":
            used_legacy = True
            if index + 1 < len(tokens):
                for part in tokens[index + 1].split(","):
                    value = part.strip()
                    if value:
                        translated.extend(["--id", value])
                index += 2
            else:
                index += 1
            continue
        alias = LEGACY_FLAG_ALIASES.get(token) or SHORT_FLAG_ALIASES.get(token)
        if alias:
            if alias != token:
                used_legacy = True
            translated.append(alias)
            if alias in BOOLEAN_FLAGS:
                index += 1
                continue
            if index + 1 < len(tokens):
                translated.append(tokens[index + 1])
                index += 2
            else:
                index += 1
            continue
        translated.append(token)
        index += 1
    if adapter_from_source:
        if not translated or translated[0] != adapter_from_source:
            translated.insert(0, adapter_from_source)
    return translated, used_legacy


def _emit_deprecation_warning(command: str) -> None:
    if os.environ.get("MEDICAL_KG_SUPPRESS_INGEST_DEPRECATED"):
        return
    message = (
        f"`{command}` is deprecated and delegates to the unified ingestion CLI. "
        "Use `med ingest <adapter>` instead."
    )
    print(f"Warning: {message}", file=sys.stderr)


def _run_unified_cli(argv: list[str], *, log_usage: bool) -> int:
    from Medical_KG.ingestion import cli as ingestion_cli

    normalized = list(argv) or ["--help"]
    if log_usage:
        logging.getLogger("Medical_KG.cli").warning("Delegating ingestion command: %s", " ".join(normalized))
    return ingestion_cli.main(["ingest", *normalized])


def _command_ingest(args: argparse.Namespace) -> int:
    argv = list(getattr(args, "argv", []))
    translated, used_legacy = _translate_legacy_args(argv)
    if used_legacy:
        _emit_deprecation_warning("med ingest")
    return _run_unified_cli(translated, log_usage=used_legacy)


def _command_ingest_legacy(args: argparse.Namespace) -> int:
    argv = list(getattr(args, "argv", []))
    translated, _ = _translate_legacy_args(argv)
    _emit_deprecation_warning("med ingest-legacy")
    return _run_unified_cli(translated, log_usage=True)


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

    # PDF processing commands
    ingest_pdf = subparsers.add_parser("ingest-pdf", help="Download PDF and register in ledger")
    ingest_pdf.add_argument("--uri", required=True, help="PDF URL")
    ingest_pdf.add_argument("--doc-key", required=True, help="Document identifier")
    ingest_pdf.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    ingest_pdf.set_defaults(func=_command_ingest_pdf)

    mineru = subparsers.add_parser("mineru-run", help="Execute MinerU against queued PDFs")
    mineru.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    mineru.add_argument("--doc-key", help="Process a single document key")
    mineru.add_argument("--fail-if-no-gpu", action="store_true", help="Exit 99 if GPU unavailable")
    mineru.set_defaults(func=_command_mineru_run)

    postpdf = subparsers.add_parser(
        "postpdf-start", help="Trigger downstream processing for MinerU outputs"
    )
    postpdf.add_argument("--config-dir", type=Path, default=None, help="Config directory")
    postpdf.add_argument(
        "--steps",
        default="ir->chunk->facet->embed->index",
        help="Pipeline steps to launch",
    )
    postpdf.set_defaults(func=_command_postpdf)

    # Data ingestion commands
    ingest = subparsers.add_parser(
        "ingest",
        help="Run data ingestion via the unified CLI",
        add_help=False,
    )
    ingest.set_defaults(func=_command_ingest)

    ingest_legacy = subparsers.add_parser(
        "ingest-legacy",
        help="Deprecated ingestion command (delegates to unified CLI)",
        add_help=False,
    )
    ingest_legacy.set_defaults(func=_command_ingest_legacy)

    original_parse_known_args = parser.parse_known_args

    def _parse_args(args: list[str] | None = None, namespace: argparse.Namespace | None = None) -> argparse.Namespace:
        namespace_obj, remainder = original_parse_known_args(args, namespace)
        command = getattr(namespace_obj, "command", None)
        if command in {"ingest", "ingest-legacy"}:
            setattr(namespace_obj, "argv", remainder)
        elif remainder:
            parser.error(f"unrecognized arguments: {' '.join(remainder)}")
        else:
            setattr(namespace_obj, "argv", [])
        return namespace_obj

    parser.parse_args = _parse_args  # type: ignore[assignment]

    # Licensing commands
    licensing = subparsers.add_parser("licensing", help="Licensing commands")
    licensing_subparsers = licensing.add_subparsers(dest="licensing_command", required=True)
    licensing_validate = licensing_subparsers.add_parser("validate", help="Validate licenses.yml")
    licensing_validate.add_argument("--licenses", type=Path, default=Path("licenses.yml"))
    licensing_validate.set_defaults(func=_command_licensing_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
