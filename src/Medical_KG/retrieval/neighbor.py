"""Merges neighboring chunks to reduce redundancy."""
from __future__ import annotations

from typing import Iterable, List

from .models import RetrievalResult


class NeighborMerger:
    def __init__(self, *, min_cosine: float, max_tokens: int) -> None:
        self._min_cosine = min_cosine
        self._max_tokens = max_tokens

    def merge(self, results: Iterable[RetrievalResult]) -> List[RetrievalResult]:
        merged: List[RetrievalResult] = []
        results_iter = list(results)
        for result in results_iter:
            if not merged:
                merged.append(result)
                continue
            previous = merged[-1]
            if result.doc_id == previous.doc_id and result.metadata.get("cosine", 0.0) >= self._min_cosine:
                combined_text = previous.text
                if len(combined_text) + len(result.text) <= self._max_tokens:
                    combined_text = f"{previous.text}\n{result.text}"
                    merged[-1] = previous.clone_with_score(
                        max(previous.score, result.score),
                        rerank=previous.scores.rerank,
                    )
                    merged[-1].text = combined_text
                    continue
            merged.append(result)
        return merged


__all__ = ["NeighborMerger"]
