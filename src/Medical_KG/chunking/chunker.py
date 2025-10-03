"""Semantic chunking implementation using coherence and clinical intent."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from Medical_KG.embeddings import QwenEmbeddingClient

from .document import Document, Section
from .profiles import ChunkingProfile, get_profile
from .tagger import ClinicalIntent, ClinicalIntentTagger

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_HEADING_PATTERN = re.compile(r"^#{1,3}\s|^[A-Z][A-Z\s]{4,}$")
_EFFECT_PAIR_PATTERN = re.compile(r"(hazard ratio|odds ratio|risk ratio|95% CI|p=)", re.IGNORECASE)
_LIST_ITEM_PATTERN = re.compile(r"^(?:[-*•]|\d+\.)\s")
_CITATION_TRAIL_PATTERN = re.compile(r"\[[0-9,\s]+\]$")
_TITRATION_PATTERN = re.compile(r"titr\w+|increase by|decrease by", re.IGNORECASE)


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    start: int
    end: int
    tokens: int
    intent: ClinicalIntent
    section: Optional[str] = None
    section_loinc: Optional[str] = None
    title_path: Optional[str] = None
    table_lines: Optional[List[str]] = None
    overlap_with_prev: Optional[dict[str, object]] = None
    facet_json: Optional[dict[str, object]] = None
    facet_type: Optional[str] = None
    coherence_score: float = 0.0
    table_html: Optional[str] = None
    table_digest: Optional[str] = None
    embedding_qwen: Optional[List[float]] = None
    splade_terms: Optional[dict[str, float]] = None
    facet_embedding_qwen: Optional[List[float]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_embedding_text(self) -> str:
        return self.text

    def to_sparse_text(self) -> str:
        parts: list[str] = [self.text]
        if self.title_path:
            parts.append(self.title_path)
        if self.table_lines:
            parts.extend(self.table_lines)
        if self.facet_json:
            parts.append(json.dumps(self.facet_json, sort_keys=True))
        return "\n".join(part for part in parts if part)


@dataclass(slots=True)
class Sentence:
    text: str
    start: int
    end: int
    section: Optional[Section]
    is_overlap: bool = False

    @property
    def tokens(self) -> int:
        return len(self.text.split())


def _sentence_split(text: str) -> List[Tuple[str, int, int]]:
    spans: List[Tuple[str, int, int]] = []
    last = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        end = match.start() + 1
        sentence = text[last:end].strip()
        if sentence:
            spans.append((sentence, last, end))
        last = match.end()
    tail = text[last:].strip()
    if tail:
        spans.append((tail, last, len(text)))
    return spans


def _lexical_coherence(a: str, b: str) -> float:
    def vectorise(sentence: str) -> dict[str, float]:
        counts = {}
        for token in re.findall(r"[A-Za-z0-9]+", sentence.lower()):
            counts[token] = counts.get(token, 0) + 1
        return counts

    vec_a = vectorise(a)
    vec_b = vectorise(b)
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a.get(token, 0) * vec_b.get(token, 0) for token in set(vec_a) | set(vec_b))
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ChunkIdGenerator:
    """Deterministically derive chunk identifiers."""

    def __init__(self, doc_id: str) -> None:
        self._doc_id = doc_id
        self._counter = 0

    def next(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        chunk_id = f"{self._doc_id}:c{self._counter}#{digest}"
        self._counter += 1
        return chunk_id


@dataclass(slots=True)
class SemanticChunker:
    profile: ChunkingProfile
    tagger: ClinicalIntentTagger = field(default_factory=ClinicalIntentTagger)
    embedding_client: QwenEmbeddingClient = field(
        default_factory=lambda: QwenEmbeddingClient(dimension=32, batch_size=64)
    )

    def chunk(self, document: Document) -> List[Chunk]:
        sentences = self._prepare_sentences(document)
        if not sentences:
            return []
        chunk_id_gen = ChunkIdGenerator(document.doc_id)
        chunks: List[Chunk] = []
        current_sentences: List[Sentence] = []
        current_tokens = 0
        previous_sentence: Optional[Sentence] = None
        previous_chunk: Optional[Chunk] = None
        for sentence in sentences:
            is_heading = bool(_HEADING_PATTERN.match(sentence.text.strip()))
            coherence = (
                self._sentence_similarity(previous_sentence.text, sentence.text)
                if previous_sentence
                else 1.0
            )
            hard_boundary = is_heading or self._section_changed(previous_sentence, sentence)
            limit_reached = current_tokens + sentence.tokens > int(self.profile.target_tokens * 1.5)
            coherence_drop = coherence < self.profile.tau_coherence
            guardrail = self._should_delay_boundary(previous_sentence, sentence)
            if (
                current_sentences
                and (hard_boundary or limit_reached or coherence_drop)
                and not guardrail
            ):
                chunk = self._create_chunk(
                    document, current_sentences, chunk_id_gen, previous_chunk
                )
                chunks.append(chunk)
                previous_chunk = chunk
                current_sentences = self._start_with_overlap(previous_chunk)
                current_tokens = sum(sent.tokens for sent in current_sentences)
            current_sentences.append(sentence)
            current_tokens += sentence.tokens
            previous_sentence = sentence
        if current_sentences:
            chunk = self._create_chunk(document, current_sentences, chunk_id_gen, previous_chunk)
            chunks.append(chunk)
        return chunks

    def _prepare_sentences(self, document: Document) -> List[Sentence]:
        sentences: List[Sentence] = []
        tables = list(document.iter_tables())
        text = document.text
        for raw_sentence, start, end in _sentence_split(text):
            containing = next((table for table in tables if start <= table.start < end), None)
            if containing:
                before = raw_sentence[: containing.start - start].strip()
                after = raw_sentence[containing.end - start :].strip()
                if before:
                    section = document.section_for_offset(start)
                    sentences.append(
                        Sentence(text=before, start=start, end=containing.start, section=section)
                    )
                if after:
                    section = document.section_for_offset(containing.end)
                    sentences.append(
                        Sentence(text=after, start=containing.end, end=end, section=section)
                    )
                continue
            section = document.section_for_offset(start)
            sentences.append(Sentence(text=raw_sentence, start=start, end=end, section=section))
        # add tables as sentences to enforce atomic chunks
        for table in tables:
            table_text = text[table.start : table.end]
            sentences.append(
                Sentence(
                    text=table_text,
                    start=table.start,
                    end=table.end,
                    section=document.section_for_offset(table.start),
                )
            )
        sentences.sort(key=lambda s: s.start)
        return sentences

    def _create_chunk(
        self,
        document: Document,
        sentences: Sequence[Sentence],
        chunk_id_gen: ChunkIdGenerator,
        previous_chunk: Optional[Chunk],
    ) -> Chunk:
        text = " ".join(sentence.text.strip() for sentence in sentences)
        chunk_id = chunk_id_gen.next(text)
        start = sentences[0].start
        end = sentences[-1].end
        tokens = sum(sentence.tokens for sentence in sentences)
        effective_sentences = [
            sentence for sentence in sentences if not sentence.is_overlap
        ] or list(sentences)
        sections = [
            sentence.section.name if sentence.section else None for sentence in effective_sentences
        ]
        intents = self.tagger.tag_sentences(
            [sentence.text for sentence in effective_sentences], sections=sections
        )
        dominant_intent = self.tagger.dominant_intent(intents)
        section = sections[-1]
        last_effective = effective_sentences[-1]
        section_loinc = last_effective.section.loinc_code if last_effective.section else None
        overlap_info = None
        if previous_chunk:
            overlap_tokens, _, overlap_start, overlap_end = self._overlap_window(previous_chunk)
            if overlap_tokens:
                overlap_info = {
                    "chunk_id": previous_chunk.chunk_id,
                    "token_window": overlap_tokens,
                    "start": overlap_start,
                    "end": overlap_end,
                }
        table_html = None
        table_digest = None
        table_lines: Optional[List[str]] = None
        for table in document.iter_tables():
            if table.start >= start and table.end <= end:
                table_html = table.html
                table_digest = self._summarise_table(table.html, fallback=table.digest)
                table_lines = self._extract_table_lines(table.html)
        title_path = self._derive_title_path(section)
        return Chunk(
            chunk_id=chunk_id,
            doc_id=document.doc_id,
            text=text,
            start=start,
            end=end,
            tokens=tokens,
            intent=dominant_intent,
            section=section,
            section_loinc=section_loinc,
            title_path=title_path,
            table_lines=table_lines,
            overlap_with_prev=overlap_info,
            coherence_score=self._chunk_coherence(sentences),
            table_html=table_html,
            table_digest=table_digest,
        )

    def _chunk_coherence(self, sentences: Sequence[Sentence]) -> float:
        if len(sentences) == 1:
            return 1.0
        scores = []
        for left, right in zip(sentences, sentences[1:]):
            scores.append(self._sentence_similarity(left.text, right.text))
        if not scores:
            return 1.0
        return sum(scores) / len(scores)

    def _section_changed(
        self, previous_sentence: Optional[Sentence], current_sentence: Sentence
    ) -> bool:
        if not previous_sentence or not previous_sentence.section:
            return False
        return previous_sentence.section != current_sentence.section

    def _start_with_overlap(self, previous_chunk: Optional[Chunk]) -> List[Sentence]:
        if not previous_chunk:
            return []
        overlap_tokens, overlap_text, overlap_start, overlap_end = self._overlap_window(
            previous_chunk
        )
        if overlap_tokens == 0 or not overlap_text:
            return []
        synthetic_sentence = Sentence(
            text=overlap_text,
            start=overlap_start,
            end=overlap_end,
            section=None,
            is_overlap=True,
        )
        return [synthetic_sentence]

    def _sentence_similarity(self, left: str, right: str) -> float:
        lexical = _lexical_coherence(left, right)
        embeddings = self.embedding_client.embed([left, right])
        dense = self._cosine_dense(embeddings[0], embeddings[1])
        return (lexical + dense) / 2

    def _cosine_dense(self, a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)

    def _should_delay_boundary(
        self,
        previous_sentence: Optional[Sentence],
        current_sentence: Sentence,
    ) -> bool:
        if previous_sentence is None:
            return False
        previous_text = previous_sentence.text.strip()
        current_text = current_sentence.text.strip()
        if _EFFECT_PAIR_PATTERN.search(previous_text) and _EFFECT_PAIR_PATTERN.search(current_text):
            return True
        if _LIST_ITEM_PATTERN.match(previous_text) and _LIST_ITEM_PATTERN.match(current_text):
            return True
        if _CITATION_TRAIL_PATTERN.search(previous_text) and current_text.lower().startswith("see"):
            return True
        if previous_sentence.section and previous_sentence.section == current_sentence.section:
            if _TITRATION_PATTERN.search(previous_text) or _TITRATION_PATTERN.search(current_text):
                return True
        return False

    def _summarise_table(self, html: str, *, fallback: Optional[str] = None) -> str | None:
        text = " ".join(re.findall(r">([^<>]+)<", html))
        text = text.strip()
        if not text and fallback:
            text = fallback
        if not text:
            return None
        tokens = text.split()
        if len(tokens) > 200:
            tokens = tokens[:200]
        return " ".join(tokens)

    def _extract_table_lines(self, html: str) -> List[str]:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL)
        lines: List[str] = []
        for row in rows:
            cells = re.findall(r">([^<>]+)<", row)
            value = " | ".join(cell.strip() for cell in cells if cell.strip())
            if value:
                lines.append(value)
        return lines

    def _derive_title_path(self, section: Optional[str]) -> Optional[str]:
        if not section:
            return None
        parts = [part.strip() for part in section.replace("_", " ").split("/") if part.strip()]
        if not parts:
            return None
        return " > ".join(part.title() for part in parts)

    def _overlap_window(self, chunk: Chunk) -> tuple[int, str, int, int]:
        tokens = chunk.text.split()
        if not tokens:
            return 0, "", chunk.end, chunk.end
        overlap_tokens = min(self.profile.overlap_tokens, len(tokens))
        if overlap_tokens <= 0:
            return 0, "", chunk.end, chunk.end
        window_tokens = tokens[-overlap_tokens:]
        overlap_text = " ".join(window_tokens).strip()
        if not overlap_text:
            return 0, "", chunk.end, chunk.end
        relative_start = chunk.text.rfind(overlap_text)
        if relative_start < 0:
            relative_start = max(len(chunk.text) - len(overlap_text), 0)
        start = chunk.start + relative_start
        end = start + len(overlap_text)
        return overlap_tokens, overlap_text, start, end


def select_profile(document: Document) -> ChunkingProfile:
    if document.source_system and document.source_system.lower().startswith("pmc"):
        return get_profile("imrad")
    if document.source_system and "registry" in document.source_system.lower():
        return get_profile("registry")
    if document.media_type and "spl" in document.media_type.lower():
        return get_profile("spl")
    return get_profile("guideline")


__all__ = ["Chunk", "SemanticChunker", "select_profile"]
