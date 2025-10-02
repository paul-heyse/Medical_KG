"""GPU enforcement utilities for embedding services."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

import httpx

_torch_spec = importlib.util.find_spec("torch")
if _torch_spec is not None:
    import torch  # type: ignore[import-not-found]
else:  # pragma: no cover - fallback when torch unavailable
    torch = None  # type: ignore[assignment]


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
        if torch is None or not torch.cuda.is_available():
            raise GPURequirementError("GPU required for embeddings but torch.cuda.is_available() returned False")
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
            raise GPURequirementError("GPU required for embeddings but nvidia-smi is not available") from exc
        except subprocess.SubprocessError as exc:
            raise GPURequirementError("Failed to execute nvidia-smi for GPU validation") from exc
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not names:
            raise GPURequirementError("GPU required for embeddings but no devices were reported by nvidia-smi")

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
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url)
        return response.status_code


__all__ = ["GPURequirementError", "GPUValidator"]
