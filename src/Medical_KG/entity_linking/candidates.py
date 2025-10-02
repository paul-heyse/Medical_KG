"""Candidate generation for entity linking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from Medical_KG.retrieval.fusion import reciprocal_rank_fusion

from .ner import Mention


@dataclass(slots=True)
class Candidate:
    identifier: str
    ontology: str
    score: float
    label: str
    metadata: Mapping[str, object]


class DictionaryClient:
    def search(self, text: str, *, fuzzy: bool = False) -> Sequence[Candidate]:  # pragma: no cover - interface
        raise NotImplementedError


class SparseClient:
    def search(self, text: str) -> Sequence[Candidate]:  # pragma: no cover - interface
        raise NotImplementedError


class DenseClient:
    def search(self, text: str, context: str) -> Sequence[Candidate]:  # pragma: no cover
        raise NotImplementedError


class CandidateGenerator:
    def __init__(
        self,
        *,
        dictionary: DictionaryClient,
        sparse: SparseClient,
        dense: DenseClient,
        rrf_k: int = 60,
    ) -> None:
        self._dictionary = dictionary
        self._sparse = sparse
        self._dense = dense
        self._rrf_k = rrf_k

    def generate(self, mention: Mention, context: str) -> List[Candidate]:
        lex = list(self._dictionary.search(mention.text, fuzzy=False))
        fuzzy = list(self._dictionary.search(mention.text, fuzzy=True))
        sparse = list(self._sparse.search(mention.text))
        dense = list(self._dense.search(mention.text, context))
        pools = {
            "lexical": lex + fuzzy,
            "sparse": sparse,
            "dense": dense,
        }
        rrf_scores = reciprocal_rank_fusion(
            {
                name: [
                    type("Hit", (), {"chunk_id": c.identifier, "score": c.score, "doc_id": c.ontology})
                    for c in candidates
                ]
                for name, candidates in pools.items()
            },
            k=self._rrf_k,
        )
        enriched: List[Candidate] = []
        for candidate in {c.identifier: c for pool in pools.values() for c in pool}.values():
            score = max(candidate.score, rrf_scores.get(candidate.identifier, 0.0))
            enriched.append(
                Candidate(
                    identifier=candidate.identifier,
                    ontology=candidate.ontology,
                    score=score,
                    label=candidate.label,
                    metadata=candidate.metadata,
                )
            )
        enriched.sort(key=lambda item: item.score, reverse=True)
        return enriched[:20]


__all__ = ["CandidateGenerator", "Candidate", "DictionaryClient", "SparseClient", "DenseClient"]
