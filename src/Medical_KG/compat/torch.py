"""Typed helpers for optional torch dependency."""

from __future__ import annotations

import importlib
from typing import Protocol, cast


class CudaProtocol(Protocol):
    def is_available(self) -> bool:
        ...


class TorchProtocol(Protocol):
    cuda: CudaProtocol


def load_torch() -> TorchProtocol | None:
    """Return the torch module if available, otherwise ``None``."""

    spec = importlib.util.find_spec("torch")
    if spec is None:
        return None
    module = importlib.import_module("torch")
    if not hasattr(module, "cuda"):
        return None
    return cast(TorchProtocol, module)


__all__ = ["CudaProtocol", "TorchProtocol", "load_torch"]
