"""CLI utility to migrate legacy string-based ledgers to the enum state machine."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Protocol, cast

import jsonlines
from Medical_KG.ingestion.ledger import (
    IngestionLedger,
    InvalidStateTransition,
    LedgerAuditRecord,
    LedgerState,
    coerce_state,
    validate_transition,
)
from Medical_KG.ingestion.types import JSONValue, MutableJSONMapping
from Medical_KG.ingestion.utils import ensure_json_value

LOGGER = logging.getLogger(__name__)


class _JsonLinesWriter(Protocol):
    def write(self, obj: object) -> None: ...


def _parse_timestamp(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            pass
        else:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).timestamp()
    return datetime.now(timezone.utc).timestamp()


def migrate_ledger(
    input_path: Path,
    *,
    output_path: Path | None = None,
    dry_run: bool = False,
    create_backup: bool = True,
    progress_interval: int | None = None,
) -> Path | None:
    """Perform migration returning the output path when a file is written."""

    if not input_path.exists():
        raise FileNotFoundError(f"Ledger not found: {input_path}")
    destination = output_path or input_path
    records: list[LedgerAuditRecord] = []
    state_index: dict[str, LedgerState] = {}
    warnings: list[str] = []
    total = 0
    with jsonlines.open(input_path, mode="r") as reader:
        for total, row in enumerate(cast(Iterable[Mapping[str, JSONValue]], reader), start=1):
            mapping = row if isinstance(row, Mapping) else {}
            doc_id = str(mapping.get("doc_id", ""))
            if not doc_id:
                continue
            new_state = coerce_state(str(mapping.get("state", "legacy")))
            old_state = state_index.get(doc_id, LedgerState.LEGACY)
            try:
                validate_transition(old_state, new_state)
            except InvalidStateTransition as exc:
                message = f"Invalid transition {old_state.value} -> {new_state.value} for {doc_id}: {exc}"
                LOGGER.warning(message)
                warnings.append(message)
            timestamp = _parse_timestamp(mapping.get("timestamp"))
        metadata_value = ensure_json_value(mapping.get("metadata", {}), context="migration metadata")
        if isinstance(metadata_value, Mapping):
            metadata = cast(MutableJSONMapping, metadata_value)
        else:
            metadata = cast(MutableJSONMapping, {})
            audit = LedgerAuditRecord(
                doc_id=doc_id,
                old_state=old_state,
                new_state=new_state,
                timestamp=timestamp,
                adapter=None,
                metadata=metadata,
            )
            records.append(audit)
            state_index[doc_id] = new_state
            if progress_interval and total % progress_interval == 0:
                print(f"Processed {total} ledger entries", file=sys.stderr)
    if dry_run:
        print(f"Ledger contains {len(state_index)} documents and {total} entries", file=sys.stderr)
        if warnings:
            print(f"Encountered {len(warnings)} invalid transitions", file=sys.stderr)
        return None
    if create_backup:
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")
        if not backup_path.exists():
            shutil.copy2(input_path, backup_path)
            LOGGER.info("Ledger backup created", extra={"backup": str(backup_path)})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(destination, mode="w") as handle:
        writer = cast(_JsonLinesWriter, handle)
        for record in records:
            writer.write(record.to_dict())
    IngestionLedger(destination)
    LOGGER.info("Ledger migration complete", extra={"output": str(destination), "entries": total})
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__ or "Ledger migration tool")
    parser.add_argument("--input", type=Path, required=True, help="Legacy ledger JSONL path")
    parser.add_argument("--output", type=Path, default=None, help="Output path (defaults to --input)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing output")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .bak backup alongside the input ledger",
    )
    parser.add_argument(
        "--progress",
        type=int,
        default=None,
        help="Print progress every N processed entries",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        migrate_ledger(
            args.input,
            output_path=args.output,
            dry_run=args.dry_run,
            create_backup=not args.no_backup,
            progress_interval=args.progress,
        )
    except FileNotFoundError as exc:
        parser.error(str(exc))
        return 2
    except Exception as exc:  # pragma: no cover - top level guard
        LOGGER.exception("Ledger migration failed", exc_info=exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
