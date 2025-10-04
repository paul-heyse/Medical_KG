"""Simple command-line interface for configuration management."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Protocol, cast

from Medical_KG.config.manager import (
    ConfigError,
    ConfigManager,
    ConfigSchemaValidator,
    mask_secrets,
)
from Medical_KG.config.models import PdfPipelineSettings
from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState
from Medical_KG.pdf import (
    GpuNotAvailableError,
    MinerUConfig,
    MinerURunner,
    PdfDocument,
    PdfPipeline,
    ensure_gpu,
)
from Medical_KG.security.licenses import LicenseRegistry
from Medical_KG.utils.optional_dependencies import (
    MissingDependencyError,
    get_httpx_module,
    iter_dependency_statuses,
)


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
        module = get_httpx_module()
    except MissingDependencyError as exc:  # pragma: no cover - dependency check
        raise RuntimeError(str(exc)) from exc
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
        ConfigSchemaValidator(manager.base_path / "config.schema.json").validate(
            payload, source="CLI payload"
        )
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


def _command_dependencies_check(args: argparse.Namespace) -> int:
    statuses = list(iter_dependency_statuses())
    all_installed = all(status.installed for status in statuses)
    if getattr(args, "json", False):
        payload = [
            {
                "feature": status.feature_name,
                "extras_group": status.extras_group,
                "packages": list(status.packages),
                "installed": status.installed,
                "missing_packages": list(status.missing_packages),
                "install_hint": status.install_hint,
                "docs_url": status.docs_url,
            }
            for status in statuses
        ]
        indent = 2 if getattr(args, "verbose", False) else None
        print(json.dumps(payload, indent=indent))
        return 0 if all_installed else 1

    for status in statuses:
        extras = f" [{status.extras_group}]" if status.extras_group else ""
        state = "installed" if status.installed else "missing"
        print(f"{status.feature_name}{extras}: {state}")
        if status.installed:
            if getattr(args, "verbose", False):
                print(f"  packages: {', '.join(status.packages)}")
                print(f"  install: {status.install_hint}")
                if status.docs_url:
                    print(f"  docs: {status.docs_url}")
        else:
            missing = status.missing_packages or status.packages
            print(f"  missing: {', '.join(missing)}")
            print(f"  install: {status.install_hint}")
            if status.docs_url:
                print(f"  docs: {status.docs_url}")
            elif getattr(args, "verbose", False):
                print("  docs: (not provided)")
    return 0 if all_installed else 1


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
    ledger.update_state(
        args.doc_key,
        LedgerState.FETCHED,
        metadata={"uri": args.uri, "local_path": str(destination)},
        adapter="pdf-ingest",
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
    entries = ledger.entries(state=LedgerState.FETCHED)
    if args.doc_key:
        entries = [entry for entry in entries if entry.doc_id == args.doc_key]
    if not entries:
        print("No PDFs ready for MinerU")
        return 0
    exit_code = 0
    for entry in entries:
        local_path_value = entry.metadata.get("local_path")
        if not isinstance(local_path_value, str) or not local_path_value:
            print(f"Skipping {entry.doc_id}: missing local_path", file=sys.stderr)
            continue
        document = PdfDocument(
            doc_key=entry.doc_id,
            uri=str(entry.metadata.get("uri", "")),
            local_path=Path(local_path_value),
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
            ledger.update_state(
                entry.doc_id,
                LedgerState.FAILED,
                metadata={"error": str(exc)},
                adapter="mineru",
            )
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
    entries = list(ledger.entries(state=LedgerState.IR_READY))
    for entry in entries:
        ledger.update_state(
            entry.doc_id,
            LedgerState.EMBEDDING,
            metadata={"steps": args.steps},
            adapter="postpdf",
        )
    print(f"Triggered downstream processing for {len(entries)} document(s)")
    return 0


def _load_ledger_for_cli(args: argparse.Namespace) -> IngestionLedger:
    snapshot_dir = getattr(args, "snapshot_dir", None)
    return IngestionLedger(args.ledger_path.expanduser(), snapshot_dir=snapshot_dir)


def _command_ledger_compact(args: argparse.Namespace) -> int:
    ledger = _load_ledger_for_cli(args)
    snapshot = ledger.create_snapshot(args.output)
    print(f"Snapshot created at {snapshot}")
    return 0


def _command_ledger_validate(args: argparse.Namespace) -> int:
    ledger = _load_ledger_for_cli(args)
    totals = {
        state.value: len(ledger.get_documents_by_state(state)) for state in LedgerState
    }
    print(json.dumps({"documents_by_state": totals}, indent=2))
    return 0


def _command_ledger_stats(args: argparse.Namespace) -> int:
    ledger = _load_ledger_for_cli(args)
    totals = {
        state.value: len(ledger.get_documents_by_state(state)) for state in LedgerState
    }
    for state, count in sorted(totals.items()):
        print(f"{state}: {count}")
    return 0


def _command_ledger_stuck(args: argparse.Namespace) -> int:
    ledger = _load_ledger_for_cli(args)
    stuck = ledger.get_stuck_documents(args.hours)
    if not stuck:
        print("No stuck documents detected")
        return 0
    for document in stuck:
        duration_hours = document.duration() / 3600
        print(f"{document.doc_id}: {document.state.value} ({duration_hours:.2f}h)")
    return 0


def _command_ledger_history(args: argparse.Namespace) -> int:
    ledger = _load_ledger_for_cli(args)
    history = ledger.get_state_history(args.doc_id)
    if not history:
        print(f"No history for {args.doc_id}")
        return 0
    for record in history:
        timestamp = datetime.fromtimestamp(record.timestamp, tz=timezone.utc)
        print(
            f"{timestamp.isoformat()} {record.old_state.value} -> {record.new_state.value}"
        )
    return 0


def _command_ingest(args: argparse.Namespace) -> int:
    from Medical_KG.ingestion import cli as ingestion_cli

    argv = list(getattr(args, "argv", []))
    normalized = argv or ["--help"]
    return ingestion_cli.main(["ingest", *normalized])


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

    ledger_parser = subparsers.add_parser("ledger", help="Ledger maintenance commands")
    ledger_parser.add_argument("--ledger-path", type=Path, required=True, help="Ledger JSONL path")
    ledger_parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=None,
        help="Optional snapshot directory override",
    )
    ledger_sub = ledger_parser.add_subparsers(dest="ledger_command", required=True)

    ledger_compact = ledger_sub.add_parser("compact", help="Create ledger snapshot")
    ledger_compact.add_argument("--output", type=Path, default=None, help="Snapshot output path")
    ledger_compact.set_defaults(func=_command_ledger_compact)

    ledger_validate = ledger_sub.add_parser("validate", help="Validate ledger integrity")
    ledger_validate.set_defaults(func=_command_ledger_validate)

    ledger_stats = ledger_sub.add_parser("stats", help="Display ledger state distribution")
    ledger_stats.set_defaults(func=_command_ledger_stats)

    ledger_stuck = ledger_sub.add_parser("stuck", help="List documents stuck in non-terminal states")
    ledger_stuck.add_argument("--hours", type=int, default=24, help="Threshold in hours")
    ledger_stuck.set_defaults(func=_command_ledger_stuck)

    ledger_history = ledger_sub.add_parser("history", help="Show document state history")
    ledger_history.add_argument("doc_id", help="Document identifier")
    ledger_history.set_defaults(func=_command_ledger_history)

    # Data ingestion commands
    ingest = subparsers.add_parser(
        "ingest",
        help="Run data ingestion via the unified CLI",
        add_help=False,
    )
    ingest.set_defaults(func=_command_ingest)

    original_parse_known_args = parser.parse_known_args

    def _parse_args(
        args: list[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        namespace_obj, remainder = original_parse_known_args(args, namespace)
        command = getattr(namespace_obj, "command", None)
        if command == "ingest":
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

    dependencies = subparsers.add_parser(
        "dependencies", help="Optional dependency diagnostics"
    )
    dependency_subparsers = dependencies.add_subparsers(
        dest="dependencies_command", required=True
    )
    dependencies_check = dependency_subparsers.add_parser(
        "check", help="Show optional dependency installation status"
    )
    dependencies_check.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output"
    )
    dependencies_check.add_argument(
        "--verbose", action="store_true", help="Show package lists and docs"
    )
    dependencies_check.set_defaults(func=_command_dependencies_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
