"""Candidate generation for entity linking."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import List, Mapping, MutableMapping, Sequence, Tuple, cast

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
    def search(
        self, text: str, *, fuzzy: bool = False
    ) -> Sequence[Candidate]:  # pragma: no cover - interface
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
        cache_size: int = 128,
    ) -> None:
        self._dictionary = dictionary
        self._sparse = sparse
        self._dense = dense
        self._rrf_k = rrf_k
        self._cache_size = cache_size
        self._cache: MutableMapping[Tuple[str, str], Tuple[Candidate, ...]] = OrderedDict()

    def generate(self, mention: Mention, context: str) -> List[Candidate]:
        cache_key = (mention.text.lower(), context)
        cached = self._cache.get(cache_key)
        if cached is not None:
            # Move key to the end to reflect recent use
            cast(OrderedDict[Tuple[str, str], Tuple[Candidate, ...]], self._cache).move_to_end(
                cache_key
            )
            return [replace(candidate) for candidate in cached]

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
                    type(
                        "Hit",
                        (),
                        {"chunk_id": c.identifier, "score": c.score, "doc_id": c.ontology},
                    )
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
        top = tuple(enriched[:20])
        self._cache[cache_key] = top
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return [replace(candidate) for candidate in top]


__all__ = ["CandidateGenerator", "Candidate", "DictionaryClient", "SparseClient", "DenseClient"]
