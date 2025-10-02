"""MinerU runner integration."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping

from .gpu import CommandRunner, SubprocessRunner


@dataclass(slots=True)
class MinerUArtifacts:
    markdown: Path
    blocks: Path
    tables: Path
    offset_map: Path


@dataclass(slots=True)
class MinerURunResult:
    doc_key: str
    artifacts: MinerUArtifacts
    metadata: Mapping[str, object]


@dataclass(slots=True)
class MinerUConfig:
    binary: str = "mineru"
    ocr_mode: str = "auto"
    table_format: str = "html"
    workers: int = 1
    output_dir: Path = Path("./artifacts")


class MinerURunner:
    def __init__(self, config: MinerUConfig, *, runner: CommandRunner | None = None) -> None:
        self._config = config
        self._runner = runner or SubprocessRunner()
        self._config.output_dir.mkdir(parents=True, exist_ok=True)

    def command(self, pdf_path: Path, doc_key: str) -> list[str]:
        output_dir = self._config.output_dir / doc_key
        output_dir.mkdir(parents=True, exist_ok=True)
        return [
            self._config.binary,
            "--input",
            str(pdf_path),
            "--output",
            str(output_dir),
            "--ocr",
            self._config.ocr_mode,
            "--tables",
            self._config.table_format,
        ]

    def run(self, pdf_path: Path, doc_key: str) -> MinerURunResult:
        cmd = self.command(pdf_path, doc_key)
        process = self._runner.run(cmd)
        if process.returncode != 0:
            raise RuntimeError(process.stderr or "MinerU exited with non-zero status")
        output_dir = self._config.output_dir / doc_key
        artifacts = MinerUArtifacts(
            markdown=output_dir / "markdown.json",
            blocks=output_dir / "blocks.json",
            tables=output_dir / "tables.html",
            offset_map=output_dir / "offset_map.json",
        )
        metadata = {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "worker_count": self._config.workers,
        }
        return MinerURunResult(doc_key=doc_key, artifacts=artifacts, metadata=metadata)


__all__ = ["MinerURunner", "MinerURunResult", "MinerUArtifacts", "MinerUConfig"]
