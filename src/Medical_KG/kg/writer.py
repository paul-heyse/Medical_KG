from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping


@dataclass(slots=True)
class WriteStatement:
    cypher: str
    parameters: Dict[str, Any]


class KnowledgeGraphWriter:
    """Generates Cypher statements for Neo4j upserts."""

    def __init__(self) -> None:
        self._statements: list[WriteStatement] = []

    @property
    def statements(self) -> Iterable[WriteStatement]:
        return list(self._statements)

    def write_document(self, payload: Mapping[str, Any]) -> None:
        cypher = (
            "MERGE (d:Document {id: $id}) "
            "SET d += {source: $source, uri: $uri, title: $title, language: $language, publication_date: $publication_date, meta: $meta, updated_at: timestamp()}"
        )
        params = {
            "id": payload["id"],
            "source": payload.get("source"),
            "uri": payload.get("uri"),
            "title": payload.get("title"),
            "language": payload.get("language"),
            "publication_date": payload.get("publication_date"),
            "meta": payload.get("meta", {}),
        }
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_chunk(self, payload: Mapping[str, Any]) -> None:
        cypher = (
            "MERGE (c:Chunk {id: $id}) SET c += {text: $text, section: $section, start: $start, end: $end, token_count: $token_count, intent: $intent, path: $path}"  # noqa: E501
        )
        params = {
            "id": payload["id"],
            "text": payload.get("text"),
            "section": payload.get("section"),
            "start": payload.get("start"),
            "end": payload.get("end"),
            "token_count": payload.get("token_count"),
            "intent": payload.get("intent"),
            "path": payload.get("path"),
        }
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_relationship(self, rel_type: str, start_id: str, end_id: str, properties: Mapping[str, Any] | None = None) -> None:
        cypher = (
            "MATCH (a {id: $start_id}) MATCH (b {id: $end_id}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += $properties"
        )
        params = {"start_id": start_id, "end_id": end_id, "properties": dict(properties or {})}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def clear(self) -> None:
        self._statements.clear()
