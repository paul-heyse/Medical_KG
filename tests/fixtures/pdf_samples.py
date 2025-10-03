"""Reusable PDF fixtures for MinerU and catalog tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_sample_pdf(tmp_path: Path, name: str, *, content: bytes | None = None) -> Path:
    pdf_path = tmp_path / name
    payload = content or b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF"
    pdf_path.write_bytes(payload)
    return pdf_path


def write_mineru_block_json(
    tmp_path: Path,
    blocks: Iterable[dict[str, Any]],
    *,
    name: str = "blocks.json",
) -> Path:
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"blocks": list(blocks)}), encoding="utf-8")
    return target


def write_mineru_table_json(
    tmp_path: Path,
    tables: Iterable[dict[str, Any]],
    *,
    name: str = "tables.json",
) -> Path:
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"tables": list(tables)}), encoding="utf-8")
    return target


def sample_concept_lines() -> dict[str, str]:
    return {
        "umls": "C123|ENG|P|L0000001|PF|S0000001|Y|Aspirin|aspirin|0|N|256|256|S|PF|256|",
        "rxnorm": "123|RXNORM|T1|Aspirin|IN|",  # simplified RRF row
        "snomed": "123456|FSN|Aspirin (product)|",
    }


def sample_license_policy() -> dict[str, Any]:
    return {
        "buckets": {"open": True, "restricted": False, "proprietary": False},
        "loaders": {"SNOMED": {"enabled": False}},
    }
