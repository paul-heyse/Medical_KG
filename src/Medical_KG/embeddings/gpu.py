"""GPU enforcement utilities for embedding services."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Optional

from Medical_KG.compat import create_client, load_torch


class GPURequirementError(RuntimeError):
    """Raised when GPU preconditions are not satisfied."""


@dataclass(slots=True)
class GPUValidator:
    """Validate GPU availability, CUDA visibility, and vLLM health."""

    require_gpu_env: str = "REQUIRE_GPU"
    http_getter: Optional[Callable[[str], int]] = None

    def should_require_gpu(self) -> bool:
        value = os.environ.get(self.require_gpu_env, "1").lower()
        return value not in {"0", "false", "no"}

    def validate(self) -> None:
        if not self.should_require_gpu():
            return
        torch_module = load_torch()
        if (
            torch_module is None
            or not bool(getattr(torch_module, "cuda", None))
            or not torch_module.cuda.is_available()
        ):
            raise GPURequirementError(
                "GPU required for embeddings but torch.cuda.is_available() returned False"
            )
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
        except FileNotFoundError as exc:  # pragma: no cover - extremely unlikely in tests
            raise GPURequirementError(
                "GPU required for embeddings but nvidia-smi is not available"
            ) from exc
        except subprocess.SubprocessError as exc:
            raise GPURequirementError("Failed to execute nvidia-smi for GPU validation") from exc
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not names:
            raise GPURequirementError(
                "GPU required for embeddings but no devices were reported by nvidia-smi"
            )
        mem_info = getattr(torch_module.cuda, "mem_get_info", None)
        if callable(mem_info):
            free_mem, total_mem = mem_info()
            if total_mem is None or float(total_mem) <= 0.0:
                raise GPURequirementError("GPU reported invalid memory capacity")

    def validate_vllm(self, endpoint: str) -> None:
        if not self.should_require_gpu():
            return
        url = endpoint.rstrip("/") + "/health"
        status_code = self._get(url)
        if status_code != 200:
            raise GPURequirementError(f"vLLM health check at {url} returned status {status_code}")

    def _get(self, url: str) -> int:
        if self.http_getter:
            return self.http_getter(url)
        client = create_client(timeout=2.0)
        try:
            response = client.get(url)
            return response.status_code
        finally:
            client.close()


def enforce_gpu_or_exit(
    *, endpoint: str | None = None, validator: GPUValidator | None = None
) -> None:
    """Validate GPU availability and exit with code 99 on failure."""

    validator = validator or GPUValidator()
    try:
        validator.validate()
        if endpoint:
            validator.validate_vllm(endpoint)
    except GPURequirementError as exc:  # pragma: no cover - exercised in tests
        message = f"GPU enforcement failed: {exc}"
        print(message, file=sys.stderr)
        raise SystemExit(99) from exc


__all__ = ["GPURequirementError", "GPUValidator", "enforce_gpu_or_exit"]
