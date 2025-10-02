"""Domain-specific chunking profiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ChunkingProfile:
    name: str
    target_tokens: int
    overlap_tokens: int
    tau_coherence: float


PROFILES: Dict[str, ChunkingProfile] = {
    "imrad": ChunkingProfile(name="imrad", target_tokens=400, overlap_tokens=75, tau_coherence=0.15),
    "registry": ChunkingProfile(name="registry", target_tokens=350, overlap_tokens=50, tau_coherence=0.15),
    "spl": ChunkingProfile(name="spl", target_tokens=450, overlap_tokens=100, tau_coherence=0.12),
    "guideline": ChunkingProfile(name="guideline", target_tokens=350, overlap_tokens=60, tau_coherence=0.12),
}


def get_profile(name: str) -> ChunkingProfile:
    key = name.lower()
    if key not in PROFILES:
        raise KeyError(f"Unknown chunking profile: {name}")
    return PROFILES[key]


__all__ = ["ChunkingProfile", "PROFILES", "get_profile"]
