"""FastAPI router implementing the public APIs."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from Medical_KG.api.auth import Authenticator, Principal, build_default_authenticator
from Medical_KG.api.models import (
    ChunkResponse,
    ExtractionRequest,
    ExtractionResponse,
    FacetGenerationRequest,
    FacetGenerationResponse,
    HealthResponse,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveResult,
    VersionResponse,
)
from Medical_KG.extraction.models import ExtractionType
from Medical_KG.extraction.service import ClinicalExtractionService
from Medical_KG.facets.models import AdverseEventFacet, DoseFacet, EndpointFacet, FacetModel
from Medical_KG.facets.service import Chunk as FacetChunk
from Medical_KG.facets.service import FacetService
from Medical_KG.services.chunks import ChunkRepository
from Medical_KG.services.retrieval import RetrievalResult as RetrievalResultModel
from Medical_KG.services.retrieval import RetrievalService


class IdempotencyConflict(RuntimeError):
    """Raised when an idempotency key collides with a different payload."""


class IdempotencyCache:
    """Stores idempotent responses keyed by header + body hash."""

    def __init__(self, *, ttl_seconds: int = 60 * 60 * 24) -> None:
        self._ttl = ttl_seconds
        self._cache: Dict[str, tuple[int, str, bytes]] = {}

    def _cleanup(self, now: int) -> None:
        expired = [key for key, (ts, _hash, _resp) in self._cache.items() if now - ts > self._ttl]
        for key in expired:
            self._cache.pop(key, None)

    def resolve(self, key: str | None, body: bytes, *, now: int) -> bytes | None:
        if not key:
            return None
        digest = hashlib.sha256(body).hexdigest()
        self._cleanup(now)
        record = self._cache.get(key)
        if record is None:
            return None
        ts, stored_digest, response = record
        if stored_digest != digest:
            raise IdempotencyConflict("Idempotency key already used with different request")
        return response

    def store(self, key: str | None, body: bytes, response: bytes, *, now: int) -> None:
        if not key:
            return
        digest = hashlib.sha256(body).hexdigest()
        self._cleanup(now)
        existing = self._cache.get(key)
        if existing is not None and existing[1] != digest:
            raise IdempotencyConflict("Idempotency key already used with different request")
        self._cache[key] = (now, digest, response)


class RateLimiter:
    """Naive fixed-window rate limiter for tests."""

    def __init__(self, *, limit: int = 60, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._buckets: Dict[str, tuple[int, int]] = {}

    def check(self, principal: Principal, *, now: int) -> tuple[bool, int, int]:
        bucket = now // self._window
        current_bucket, count = self._buckets.get(principal.subject, (bucket, 0))
        if current_bucket != bucket:
            current_bucket, count = bucket, 0
        limited = count >= self._limit
        new_count = count if limited else count + 1
        self._buckets[principal.subject] = (current_bucket, new_count)
        remaining = max(self._limit - new_count, 0)
        reset = (current_bucket + 1) * self._window
        return limited, remaining, reset

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window(self) -> int:
        return self._window


class ApiRouter(APIRouter):
    def __init__(
        self,
        *,
        authenticator: Authenticator | None = None,
        chunk_repository: ChunkRepository | None = None,
        facet_service: FacetService | None = None,
        extraction_service: ClinicalExtractionService | None = None,
        retrieval_service: RetrievalService | None = None,
    ) -> None:
        super().__init__()
        self._authenticator = authenticator or build_default_authenticator()
        self._chunks = chunk_repository or ChunkRepository()
        self._facets = facet_service or FacetService()
        self._extractions = extraction_service or ClinicalExtractionService()
        self._retrieval = retrieval_service or RetrievalService()
        self._idempotency = IdempotencyCache()
        self._rate_limiter = RateLimiter(limit=30, window_seconds=60)
        self._register_routes()

    # dependencies ---------------------------------------------------------
    def _require_scope(self, scope: str):
        return self._authenticator.dependency(scope)

    def _apply_rate_limit(self, principal: Principal, response: Response) -> None:
        now = int(time.time())
        limited, remaining, reset = self._rate_limiter.check(principal, now=now)
        response.headers["X-RateLimit-Limit"] = str(self._rate_limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(self._rate_limiter.window)},
            )

    @staticmethod
    def _apply_license_filter(facets: list[FacetModel], tier: str) -> list[FacetModel]:
        tier = (tier or "affiliate").lower()
        if tier == "affiliate":
            return facets
        restricted = {"snomed", "snomedct", "meddra", "umls"}
        sanitized: list[FacetModel] = []
        for facet in facets:
            copy = facet.model_copy(deep=True)
            if isinstance(copy, EndpointFacet) and tier in {"public", "member"}:
                for code in copy.outcome_codes:
                    if code.system.lower() in restricted:
                        code.display = None
            elif isinstance(copy, AdverseEventFacet) and tier == "public":
                copy.meddra_pt = None
                copy.codes = [code for code in copy.codes if code.system.lower() not in restricted]
            elif isinstance(copy, DoseFacet) and tier == "public":
                copy.drug_codes = [
                    code for code in copy.drug_codes if code.system.lower() not in restricted
                ]
            sanitized.append(copy)
        return sanitized

    # route definitions ----------------------------------------------------
    def _register_routes(self) -> None:
        @self.post("/facets/generate", response_model=FacetGenerationResponse, tags=["facets"])
        async def generate_facets(
            request: Request,
            payload: FacetGenerationRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("facets:write")),
            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
            license_tier: str = Header(default="affiliate", alias="X-License-Tier"),
        ) -> FacetGenerationResponse:
            self._apply_rate_limit(principal, response)
            body = await request.body()
            now = int(time.time())
            try:
                cached = self._idempotency.resolve(idempotency_key, body, now=now)
            except IdempotencyConflict as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            if cached is not None:
                return FacetGenerationResponse.model_validate_json(cached)
            facets_by_chunk: Dict[str, list] = {}
            metadata: Dict[str, Dict[str, str]] = {}
            for chunk_id in payload.chunk_ids:
                chunk = self._chunks.get(chunk_id)
                if chunk is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown chunk {chunk_id}"
                    )
                service_chunk = FacetChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    text=chunk.text,
                    section=chunk.section,
                    table_headers=chunk.table_headers,
                )
                facets = self._facets.generate_for_chunk(service_chunk)
                filtered = self._apply_license_filter(facets, license_tier)
                facets_by_chunk[chunk_id] = filtered
                metadata[chunk_id] = {"facet_types": ",".join(facet.type.value for facet in facets)}
                record = self._facets.index_payload(chunk_id)
                if record:
                    self._retrieval.upsert(record, snippet=chunk.text)
            response_model = FacetGenerationResponse(
                facets_by_chunk=facets_by_chunk, metadata=metadata
            )
            try:
                self._idempotency.store(
                    idempotency_key, body, response_model.model_dump_json().encode(), now=now
                )
            except IdempotencyConflict as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            return response_model

        @self.get("/chunks/{chunk_id}", response_model=ChunkResponse, tags=["chunks"])
        async def get_chunk(
            chunk_id: str,
            response: Response,
            principal: Principal = Depends(self._require_scope("retrieve:read")),
            license_tier: str = Header(default="affiliate", alias="X-License-Tier"),
        ) -> ChunkResponse:
            self._apply_rate_limit(principal, response)
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
            facets = self._apply_license_filter(self._facets.get_facets(chunk_id), license_tier)
            return ChunkResponse(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                text=chunk.text,
                section=chunk.section,
                facets=facets,
            )

        @self.post("/retrieve", response_model=RetrieveResponse, tags=["retrieve"])
        async def retrieve(
            payload: RetrieveRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("retrieve:read")),
        ) -> RetrieveResponse:
            self._apply_rate_limit(principal, response)
            facet_type = payload.filters.facet_type if payload.filters else None
            results = self._retrieval.search(
                payload.query,
                facet_type=facet_type,
                top_k=payload.topK,
            )
            return RetrieveResponse(
                results=[self._map_result(result) for result in results],
                query_meta={"facet_type": facet_type},
            )

        @self.post("/extract/pico", response_model=ExtractionResponse, tags=["extract"])
        async def extract_pico(
            payload: ExtractionRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("extract:write")),
        ) -> ExtractionResponse:
            self._apply_rate_limit(principal, response)
            chunks = self._load_chunks(payload.chunk_ids)
            envelope = self._extractions.extract_many(chunks)
            filtered = self._filter_envelope(envelope, allowed={ExtractionType.PICO})
            return ExtractionResponse(envelope=filtered)

        @self.post("/extract/effects", response_model=ExtractionResponse, tags=["extract"])
        async def extract_effects(
            payload: ExtractionRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("extract:write")),
        ) -> ExtractionResponse:
            self._apply_rate_limit(principal, response)
            chunks = self._load_chunks(payload.chunk_ids)
            envelope = self._extractions.extract_many(chunks)
            filtered = self._filter_envelope(envelope, allowed={ExtractionType.EFFECT})
            return ExtractionResponse(envelope=filtered)

        @self.post("/extract/ae", response_model=ExtractionResponse, tags=["extract"])
        async def extract_ae(
            payload: ExtractionRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("extract:write")),
        ) -> ExtractionResponse:
            self._apply_rate_limit(principal, response)
            chunks = self._load_chunks(payload.chunk_ids)
            envelope = self._extractions.extract_many(chunks)
            filtered = self._filter_envelope(envelope, allowed={ExtractionType.ADVERSE_EVENT})
            return ExtractionResponse(envelope=filtered)

        @self.post("/extract/dose", response_model=ExtractionResponse, tags=["extract"])
        async def extract_dose(
            payload: ExtractionRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("extract:write")),
        ) -> ExtractionResponse:
            self._apply_rate_limit(principal, response)
            chunks = self._load_chunks(payload.chunk_ids)
            envelope = self._extractions.extract_many(chunks)
            filtered = self._filter_envelope(envelope, allowed={ExtractionType.DOSE})
            return ExtractionResponse(envelope=filtered)

        @self.post("/extract/eligibility", response_model=ExtractionResponse, tags=["extract"])
        async def extract_eligibility(
            payload: ExtractionRequest,
            response: Response,
            principal: Principal = Depends(self._require_scope("extract:write")),
        ) -> ExtractionResponse:
            self._apply_rate_limit(principal, response)
            chunks = self._load_chunks(payload.chunk_ids)
            envelope = self._extractions.extract_many(chunks)
            filtered = self._filter_envelope(envelope, allowed={ExtractionType.ELIGIBILITY})
            return ExtractionResponse(envelope=filtered)

        @self.get("/health", response_model=HealthResponse, tags=["meta"])
        async def healthcheck() -> HealthResponse:
            return HealthResponse(
                status="ok",
                services={"retrieval": "ready", "facets": "ready", "extraction": "ready"},
                timestamp=datetime.now(timezone.utc),
            )

        @self.get("/version", response_model=VersionResponse, tags=["meta"])
        async def version() -> VersionResponse:
            return VersionResponse(
                api_version="v1",
                component_versions={"facets": "v1", "extract": "v1", "retrieval": "v1"},
                model_versions={"qwen": "Qwen3-Embedding-8B", "splade": "splade-v3"},
            )

    # helper utilities -----------------------------------------------------
    def _load_chunks(self, chunk_ids: list[str]) -> list[FacetChunk]:
        chunks: list[FacetChunk] = []
        for chunk_id in chunk_ids:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown chunk {chunk_id}"
                )
            chunks.append(
                FacetChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    text=chunk.text,
                    section=chunk.section,
                    table_headers=chunk.table_headers,
                )
            )
        return chunks

    @staticmethod
    def _map_result(result: RetrievalResultModel) -> RetrieveResult:
        return RetrieveResult(
            chunk_id=result.chunk_id,
            score=result.score,
            snippet=result.snippet,
            facet_types=result.facet_types,
        )

    @staticmethod
    def _filter_envelope(envelope, *, allowed: set[ExtractionType]):
        filtered = [item for item in envelope.payload if item.type in allowed]
        return envelope.model_copy(update={"payload": filtered})

    # utilities used by tests ---------------------------------------------
    @property
    def chunk_repository(self) -> ChunkRepository:
        return self._chunks


__all__ = ["ApiRouter"]
