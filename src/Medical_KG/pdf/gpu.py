"""GPU enforcement utilities for MinerU pipeline."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Protocol


class GpuNotAvailableError(RuntimeError):
    pass


class CommandRunner(Protocol):  # pragma: no cover - interface definition
    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        ...


@dataclass(slots=True)
class SubprocessRunner(CommandRunner):
    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=False, capture_output=True, text=True)


def detect_gpu(*, runner: CommandRunner | None = None) -> bool:
    runner = runner or SubprocessRunner()
    try:
        result = runner.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    except FileNotFoundError:
        return False
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def ensure_gpu(require_flag: bool = True, *, runner: CommandRunner | None = None) -> None:
    flag_set = os.getenv("REQUIRE_GPU", "1" if require_flag else "0") == "1"
    if not flag_set and not require_flag:
        return
    if not detect_gpu(runner=runner):
        raise GpuNotAvailableError("GPU required for PDF processing but not available")


__all__ = ["ensure_gpu", "detect_gpu", "GpuNotAvailableError", "CommandRunner", "SubprocessRunner"]
