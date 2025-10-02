"""Simple command-line interface for configuration management."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx
from Medical_KG.config.manager import ConfigError, ConfigManager, ConfigValidator, mask_secrets
from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.registry import available_sources, get_adapter
from Medical_KG.pdf import (
    GpuNotAvailableError,
    MinerUConfig,
    MinerURunner,
    PdfDocument,
    PdfPipeline,
    ensure_gpu,
)


def _load_manager(config_dir: Optional[Path]) -> ConfigManager:
    base_path = config_dir or Path(__file__).resolve().parent / "config"
    return ConfigManager(base_path=base_path)


def _build_pipeline(manager: ConfigManager) -> PdfPipeline:
    pdf_config = manager.config.pdf_pipeline()
    ledger_path = Path(pdf_config["ledger_path"]).expanduser()
    artifact_dir = Path(pdf_config["artifact_dir"]).expanduser()
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


def _command_ingest_pdf(args: argparse.Namespace) -> int:
    try:
        manager = _load_manager(args.config_dir)
    except ConfigError as exc:
        print(f"Unable to load configuration: {exc}")
        return 1
    pipeline_config = manager.config.pdf_pipeline()
    downloads_dir = Path(pipeline_config["artifact_dir"]).expanduser() / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    destination = downloads_dir / f"{args.doc_key}.pdf"
    try:
        with httpx.Client(timeout=30.0) as client:  # type: ignore
            response = client.get(args.uri, follow_redirects=True)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Failed to download PDF: {exc}", file=sys.stderr)
        return 1
    destination.write_bytes(response.content)
    ledger = IngestionLedger(Path(pipeline_config["ledger_path"]).expanduser())
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
    ledger = IngestionLedger(Path(pdf_config["ledger_path"]).expanduser())
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
    require_gpu = bool(pdf_config.get("require_gpu", True))
    try:
        ensure_gpu(require_flag=require_gpu)
    except GpuNotAvailableError as exc:
        print(str(exc), file=sys.stderr)
        return 99
    ledger = IngestionLedger(Path(pdf_config["ledger_path"]).expanduser())
    entries = list(ledger.entries(state="pdf_ir_ready"))
    for entry in entries:
        ledger.record(entry.doc_id, "postpdf_started", {"steps": args.steps})
    print(f"Triggered downstream processing for {len(entries)} document(s)")
    return 0


def _command_ingest(args: argparse.Namespace) -> int:
    if args.source not in available_sources():
        print(f"Unknown source '{args.source}'. Known sources: {', '.join(available_sources())}")
        return 1

    ledger = IngestionLedger(args.ledger)
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = get_adapter(args.source, context, client)

    async def _run() -> None:
        try:
            if args.batch:
                with args.batch.open() as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        params = json.loads(line)
                        results = await adapter.run(**params)
                        if args.auto:
                            print(json.dumps([res.document.doc_id for res in results]))
            else:
                results = await adapter.run()
                if args.auto:
                    print(json.dumps([res.document.doc_id for res in results]))
        finally:
            await client.aclose()

    asyncio.run(_run())
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
    ingest = subparsers.add_parser("ingest", help="Run data ingestion for a source")
    ingest.add_argument("source", choices=available_sources(), help="Source identifier")
    ingest.add_argument("--batch", type=Path, default=None, help="NDJSON batch parameters")
    ingest.add_argument(
        "--auto", action="store_true", help="Emit doc IDs for downstream automation"
    )
    ingest.add_argument(
        "--ledger",
        type=Path,
        default=Path(".ingest-ledger.jsonl"),
        help="Path to ingestion ledger JSONL",
    )
    ingest.set_defaults(func=_command_ingest)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
