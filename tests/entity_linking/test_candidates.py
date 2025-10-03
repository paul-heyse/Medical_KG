from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from Medical_KG.entity_linking.candidates import (
    Candidate,
    CandidateGenerator,
    DenseClient,
    DictionaryClient,
    SparseClient,
)
from Medical_KG.entity_linking.ner import Mention


@dataclass
class _RecordingDictionary(DictionaryClient):
    calls: list[tuple[str, bool]]
    results: Sequence[Candidate]

    def search(self, text: str, *, fuzzy: bool = False) -> Sequence[Candidate]:
        self.calls.append((text, fuzzy))
        return self.results


@dataclass
class _StaticSparse(SparseClient):
    results: Sequence[Candidate]

    def search(self, text: str) -> Sequence[Candidate]:
        return self.results


@dataclass
class _StaticDense(DenseClient):
    results: Sequence[Candidate]

    def search(self, text: str, context: str) -> Sequence[Candidate]:
        return self.results


def _candidate(identifier: str, score: float, ontology: str = "rxnorm") -> Candidate:
    return Candidate(
        identifier=identifier, ontology=ontology, score=score, label=identifier, metadata={}
    )


def _generator(
    dictionary_results: Sequence[Candidate], sparse=None, dense=None
) -> CandidateGenerator:
    dictionary = _RecordingDictionary(calls=[], results=dictionary_results)
    sparse_client = _StaticSparse(results=sparse or [])
    dense_client = _StaticDense(results=dense or [])
    return CandidateGenerator(
        dictionary=dictionary, sparse=sparse_client, dense=dense_client, cache_size=4
    )


def test_candidate_generator_ranks_by_rrf() -> None:
    mention = Mention(text="aspirin", start=0, end=7, label="drug")
    generator = _generator(
        dictionary_results=[_candidate("rx1", 0.2)],
        sparse=[_candidate("rx2", 0.9)],
        dense=[_candidate("rx3", 0.8)],
    )

    results = generator.generate(mention, context="context")

    assert [candidate.identifier for candidate in results[:2]] == ["rx2", "rx3"]


def test_candidate_generator_returns_exact_match_first() -> None:
    mention = Mention(text="aspirin", start=0, end=7, label="drug")
    generator = _generator(dictionary_results=[_candidate("rx-exact", 0.95)])

    results = generator.generate(mention, context="ctx")

    assert results[0].identifier == "rx-exact"


def test_candidate_generator_includes_fuzzy_matches() -> None:
    mention = Mention(text="aspirn", start=0, end=6, label="drug")
    fuzzy = [_candidate("rx1", 0.4)]
    generator = CandidateGenerator(
        dictionary=_RecordingDictionary(calls=[], results=fuzzy),
        sparse=_StaticSparse(results=[]),
        dense=_StaticDense(results=[]),
    )

    results = generator.generate(mention, context="ctx")
    assert results


def test_candidate_generator_handles_no_candidates() -> None:
    mention = Mention(text="unknown", start=0, end=7, label="drug")
    generator = _generator(dictionary_results=[], sparse=[], dense=[])

    assert generator.generate(mention, context="ctx") == []


def test_candidate_generator_caches_results() -> None:
    mention = Mention(text="aspirin", start=0, end=7, label="drug")
    dictionary = _RecordingDictionary(calls=[], results=[_candidate("rx1", 0.5)])
    generator = CandidateGenerator(
        dictionary=dictionary,
        sparse=_StaticSparse(results=[]),
        dense=_StaticDense(results=[]),
        cache_size=4,
    )

    first = generator.generate(mention, context="ctx")
    second = generator.generate(
        Mention(text="aspirin", start=0, end=7, label="drug"), context="ctx"
    )

    assert first == second
    assert len(dictionary.calls) == 2  # first call includes lex + fuzzy entries
    # Second invocation should rely on cache (no additional dictionary queries)
    assert dictionary.calls[-2:] == [("aspirin", False), ("aspirin", True)]
