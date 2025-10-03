"""High-level retrieval orchestration combining multiple retrievers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, Mapping, Sequence

from .caching import TTLCache
from .clients import EmbeddingClient, OpenSearchClient, Reranker, SpladeEncoder, VectorSearchClient
from .fusion import reciprocal_rank_fusion, weighted_fusion
from .intent import IntentClassifier, IntentRule
from .models import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrieverContext,
    RetrieverScores,
    RetrieverTiming,
    merge_metadata,
    normalize_filters,
)
from .neighbor import NeighborMerger
from .ontology import OntologyExpander
from .types import FusionScores, JSONValue, MultiGranularityConfig, NeighborMergeConfig


@dataclass(slots=True)
class RetrieverConfig:
    bm25_index: str
    splade_index: str
    dense_index: str
    max_top_k: int
    default_top_k: int
    rrf_k: int
    rerank_top_n: int
    weights: Mapping[str, float]
    neighbor_merge: NeighborMergeConfig
    query_cache_seconds: int
    embedding_cache_seconds: int
    expansion_cache_seconds: int
    slo_ms: float
    multi_granularity: MultiGranularityConfig


class RetrievalService:
    def __init__(
        self,
        *,
        opensearch: OpenSearchClient,
        vector: VectorSearchClient,
        embedder: EmbeddingClient,
        splade: SpladeEncoder,
        intents: Iterable[IntentRule],
        config: RetrieverConfig,
        reranker: Reranker | None = None,
        ontology: OntologyExpander | None = None,
    ) -> None:
        self._os = opensearch
        self._vector = vector
        self._embedder = embedder
        self._splade_encoder = splade
        self._intent = IntentClassifier(intents)
        self._config = config
        self._reranker = reranker
        self._ontology = ontology or OntologyExpander()
        self._query_cache = TTLCache[RetrievalResponse](config.query_cache_seconds)
        self._expansion_cache = TTLCache[Mapping[str, float]](config.expansion_cache_seconds)
        self._embedding_cache = TTLCache[Sequence[float]](config.embedding_cache_seconds)

    def _context(self, request: RetrievalRequest) -> RetrieverContext:
        intent = request.intent or self._intent.detect(request.query)
        boosts, filters = self._intent.context_for(intent)
        weights = dict(self._config.weights)
        top_k = min(max(request.top_k or self._config.default_top_k, 1), self._config.max_top_k)
        rerank_enabled = request.rerank_enabled if request.rerank_enabled is not None else True
        return RetrieverContext(
            boosts=boosts,
            filters=merge_metadata(filters, normalize_filters(request.filters)),
            top_k=top_k,
            weights=weights,
            rrf_k=self._config.rrf_k,
            rerank_top_n=self._config.rerank_top_n,
            rerank_enabled=rerank_enabled and self._reranker is not None,
            neighbor_merge=self._config.neighbor_merge,
            multi_granularity=self._config.multi_granularity,
        )

    def _cache_key(self, request: RetrievalRequest) -> str:
        payload = {
            "query": request.query,
            "top_k": request.top_k,
            "from": request.from_,
            "filters": request.filters,
            "intent": request.intent,
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def _expand(self, query: str) -> Mapping[str, float]:
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return self._expansion_cache.get_or_set(key, lambda: self._ontology.expand(query))

    def _embed(self, query: str) -> Sequence[float]:
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return self._embedding_cache.get_or_set(key, lambda: list(self._embedder.embed(query)))

    def _bm25(
        self,
        query: str,
        context: RetrieverContext,
        *,
        index: str,
        expanded_terms: Mapping[str, float],
        granularity: str = "chunk",
    ) -> list[RetrievalResult]:
        boosts = context.boosts or {}
        expanded_text = " ".join(expanded_terms.keys()) if expanded_terms else ""
        lexical_query = f"{query} {expanded_text}".strip()
        multi_match = {
            "query": lexical_query or query,
            "fields": [
                f"title_path^{boosts.get('title_path', 2.0)}",
                f"facet_json^{boosts.get('facet_json', 1.6)}",
                f"table_lines^{boosts.get('table_lines', 1.2)}",
                f"body^{boosts.get('body', 1.0)}",
            ],
            "type": "best_fields",
        }
        bool_clause: dict[str, JSONValue] = {"must": [{"multi_match": multi_match}]}
        query_clause: dict[str, JSONValue] = {"bool": bool_clause}
        body: dict[str, JSONValue] = {"query": query_clause}
        filters = [
            {"terms": {field: value}}
            for field, value in context.filters.items()
            if field not in {"date_range"}
        ]
        date_range = context.filters.get("date_range")
        if isinstance(date_range, Mapping):
            filters.append({"range": {"publication_date": date_range}})
        if filters:
            bool_clause["filter"] = filters
        hits = self._os.search(index=index, body=body, size=context.top_k)
        results: list[RetrievalResult] = []
        for hit in hits:
            chunk_id = hit.get("chunk_id")
            doc_id = hit.get("doc_id")
            if not isinstance(chunk_id, str) or not isinstance(doc_id, str):
                continue
            text = str(hit.get("text", ""))
            title_path = hit.get("title_path") if isinstance(hit.get("title_path"), str) else None
            section = hit.get("section") if isinstance(hit.get("section"), str) else None
            metadata_raw = hit.get("metadata")
            metadata = dict(metadata_raw) if isinstance(metadata_raw, Mapping) else {}
            score_raw = hit.get("score")
            score = float(score_raw) if isinstance(score_raw, (int, float)) else 0.0
            result = RetrievalResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=text,
                title_path=title_path,
                section=section,
                score=score,
                scores=RetrieverScores(bm25=score),
                start=hit.get("start") if isinstance(hit.get("start"), int) else None,
                end=hit.get("end") if isinstance(hit.get("end"), int) else None,
                metadata=merge_metadata(metadata, {"granularity": granularity}),
            )
            results.append(result)
        return results

    def _splade(self, query: str, context: RetrieverContext) -> list[RetrievalResult]:
        expanded = self._splade_encoder.expand(query)
        should: list[JSONValue] = []
        for term, weight in expanded.items():
            feature: dict[str, JSONValue] = {
                "field": "splade_terms",
                "boost": float(weight),
                "term": term,
            }
            should.append({"rank_feature": feature})
        if not should:
            return []
        bool_clause: dict[str, JSONValue] = {"should": should, "minimum_should_match": 1}
        body: dict[str, JSONValue] = {"query": {"bool": bool_clause}}
        hits = self._os.search(index=self._config.splade_index, body=body, size=context.top_k)
        results: list[RetrievalResult] = []
        for hit in hits:
            chunk_id = hit.get("chunk_id")
            doc_id = hit.get("doc_id")
            if not isinstance(chunk_id, str) or not isinstance(doc_id, str):
                continue
            score_raw = hit.get("score")
            score = float(score_raw) if isinstance(score_raw, (int, float)) else 0.0
            metadata_raw = hit.get("metadata")
            metadata = dict(metadata_raw) if isinstance(metadata_raw, Mapping) else {}
            result = RetrievalResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=str(hit.get("text", "")),
                title_path=(
                    hit.get("title_path") if isinstance(hit.get("title_path"), str) else None
                ),
                section=hit.get("section") if isinstance(hit.get("section"), str) else None,
                score=score,
                scores=RetrieverScores(splade=score),
                start=hit.get("start") if isinstance(hit.get("start"), int) else None,
                end=hit.get("end") if isinstance(hit.get("end"), int) else None,
                metadata=metadata,
            )
            results.append(result)
        return results

    def _dense(self, query: str, context: RetrieverContext) -> list[RetrievalResult]:
        embedding = self._embed(query)
        hits = self._vector.query(
            index=self._config.dense_index, embedding=embedding, top_k=context.top_k
        )
        results: list[RetrievalResult] = []
        for hit in hits:
            chunk_id = hit.get("chunk_id")
            doc_id = hit.get("doc_id")
            if not isinstance(chunk_id, str) or not isinstance(doc_id, str):
                continue
            score_raw = hit.get("score")
            score = float(score_raw) if isinstance(score_raw, (int, float)) else 0.0
            metadata_raw = hit.get("metadata")
            metadata = dict(metadata_raw) if isinstance(metadata_raw, Mapping) else {}
            metadata.setdefault("cosine", score)
            result = RetrievalResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=str(hit.get("text", "")),
                title_path=(
                    hit.get("title_path") if isinstance(hit.get("title_path"), str) else None
                ),
                section=hit.get("section") if isinstance(hit.get("section"), str) else None,
                score=score,
                scores=RetrieverScores(dense=score),
                start=hit.get("start") if isinstance(hit.get("start"), int) else None,
                end=hit.get("end") if isinstance(hit.get("end"), int) else None,
                metadata=metadata,
            )
            results.append(result)
        return results

    async def _maybe_rerank(
        self, query: str, fused: list[RetrievalResult], context: RetrieverContext
    ) -> list[RetrievalResult]:
        if not context.rerank_enabled or not self._reranker:
            return fused
        top_candidates = fused[: context.rerank_top_n]
        reranked = await self._reranker.rerank(query, top_candidates)
        merged: list[RetrievalResult] = []
        rerank_scores = {result.chunk_id: result.score for result in reranked}
        for result in fused:
            if result.chunk_id in rerank_scores:
                rerank_score = rerank_scores[result.chunk_id]
                merged.append(result.clone_with_score(rerank_score, rerank=rerank_score))
            else:
                merged.append(result)
        merged.sort(key=lambda item: item.score, reverse=True)
        return merged

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        cache_key = self._cache_key(request)
        cached = self._query_cache.get(cache_key)
        if cached:
            return cached
        started = perf_counter()
        context = self._context(request)
        intent = request.intent or self._intent.detect(request.query)
        timings: list[RetrieverTiming] = []

        def record(component: str, elapsed: float) -> None:
            timings.append(RetrieverTiming(component=component, duration_ms=elapsed * 1000))

        bm25_results: list[RetrievalResult]
        splade_results: list[RetrievalResult]
        dense_results: list[RetrievalResult]

        expanded_terms = self._expand(request.query)

        bm25_start = perf_counter()
        bm25_results = self._bm25(
            request.query,
            context,
            index=self._config.bm25_index,
            expanded_terms=expanded_terms,
            granularity="chunk",
        )
        multi_config = context.multi_granularity
        if multi_config.get("enabled", False):
            indexes_value = multi_config.get("indexes", {})
            if isinstance(indexes_value, Mapping):
                indexes = {str(key): str(value) for key, value in indexes_value.items()}
            else:
                indexes = {}
            for granularity, index in indexes.items():
                if granularity == "chunk" or not index:
                    continue
                extra = self._bm25(
                    request.query,
                    context,
                    index=index,
                    expanded_terms=expanded_terms,
                    granularity=str(granularity),
                )
                bm25_results.extend(extra)
        record("bm25", perf_counter() - bm25_start)

        splade_start = perf_counter()
        splade_results = self._splade(request.query, context)
        record("splade", perf_counter() - splade_start)

        dense_start = perf_counter()
        dense_results = self._dense(request.query, context)
        record("dense", perf_counter() - dense_start)

        pools: dict[str, Sequence[RetrievalResult]] = {
            "bm25": bm25_results,
            "splade": splade_results,
            "dense": dense_results,
        }
        fused_scores: FusionScores = weighted_fusion(pools, context.weights)
        if not fused_scores:
            fused_scores = reciprocal_rank_fusion(
                {k: list(v) for k, v in pools.items()}, k=context.rrf_k
            )
        fused_results: dict[str, RetrievalResult] = {}
        for collection in pools.values():
            for result in collection:
                fused_results.setdefault(result.chunk_id, result)
        for chunk_id, score in fused_scores.items():
            if chunk_id in fused_results:
                item = fused_results[chunk_id]
                fused_results[chunk_id] = item.clone_with_score(score, rerank=item.scores.rerank)
                fused_results[chunk_id].scores.fused = score
        fused_list = sorted(fused_results.values(), key=lambda item: item.score, reverse=True)

        rerank_start = perf_counter()
        fused_list = await self._maybe_rerank(request.query, fused_list, context)
        record("rerank", perf_counter() - rerank_start)

        neighbor_config = context.neighbor_merge
        min_cosine = float(neighbor_config["min_cosine"])
        max_tokens = int(neighbor_config["max_tokens"])
        neighbor_merger = NeighborMerger(
            min_cosine=min_cosine,
            max_tokens=max_tokens,
        )
        merged_results = neighbor_merger.merge(fused_list)
        size = context.top_k
        sliced = merged_results[request.from_ : request.from_ + size]
        total_latency = (perf_counter() - started) * 1000
        response = RetrievalResponse(
            results=sliced,
            timings=timings,
            expanded_terms=expanded_terms,
            intent=intent,
            latency_ms=total_latency,
            from_=request.from_,
            size=len(sliced),
            metadata={
                "from": request.from_,
                "top_k": context.top_k,
                "feature_flags": {
                    "rerank_enabled": context.rerank_enabled,
                },
            },
        )
        self._query_cache.set(cache_key, response)
        return response


__all__ = ["RetrievalService", "RetrieverConfig"]
