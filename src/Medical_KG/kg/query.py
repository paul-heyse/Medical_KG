from __future__ import annotations

"""High-level Cypher query builders for the CDKO-Med graph."""

import textwrap
from dataclasses import dataclass
from typing import Any, Dict, Sequence


@dataclass(slots=True)
class Query:
    """Container for a parameterised Cypher query."""

    cypher: str
    parameters: Dict[str, Any]


class KgQueryApi:
    """Pre-built query helpers covering common traversal scenarios."""

    def related_evidence(
        self,
        *,
        drug_label: str,
        condition_label: str,
        limit: int = 25,
    ) -> Query:
        """Return a Cypher query that finds evidence for a drug/condition pair."""

        cypher = textwrap.dedent(
            """
            MATCH (drug:Concept {label: $drug_label})<-[:MENTIONS]-(drug_chunk:Chunk)
            MATCH (drug_chunk)<-[:HAS_CHUNK]-(doc:Document)
            MATCH (doc)-[:REPORTS]->(e:Evidence)-[:MEASURES]->(outcome:Outcome)
            MATCH (doc)-[:HAS_CHUNK]->(cond_chunk:Chunk)-[:MENTIONS]->(condition:Concept {label: $condition_label})
            RETURN DISTINCT e AS evidence, doc AS document, outcome AS outcome
            ORDER BY coalesce(e.confidence, 0.0) DESC, doc.publication_date DESC
            LIMIT $limit
            """
        ).strip()
        params: Dict[str, Any] = {
            "drug_label": drug_label,
            "condition_label": condition_label,
            "limit": limit,
        }
        return Query(cypher=cypher, parameters=params)

    def subsumption_evidence(
        self,
        *,
        condition_label: str,
        max_depth: int = 3,
    ) -> Query:
        """Return evidence that matches a condition or any descendant concept."""

        depth = max(int(max_depth), 0)
        cypher = textwrap.dedent(
            f"""
            MATCH (root:Concept {{label: $condition_label}})
            MATCH (root)<-[:IS_A*0..{depth}]-(descendant:Concept)
            MATCH (descendant)<-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(doc:Document)
            MATCH (doc)-[:REPORTS]->(e:Evidence)-[:MEASURES]->(outcome:Outcome)
            RETURN DISTINCT descendant AS concept, e AS evidence, outcome AS outcome, doc AS document
            ORDER BY concept.label, coalesce(e.confidence, 0.0) DESC
            """
        ).strip()
        params: Dict[str, Any] = {"condition_label": condition_label}
        return Query(cypher=cypher, parameters=params)

    def provenance_trace(self, *, evidence_id: str) -> Query:
        """Return provenance for an evidence assertion and its variables."""

        cypher = textwrap.dedent(
            """
            MATCH (e:Evidence {id: $evidence_id})
            OPTIONAL MATCH (e)-[:WAS_GENERATED_BY]->(activity:ExtractionActivity)
            OPTIONAL MATCH (e)-[:DERIVES_FROM]->(variable:EvidenceVariable)
            OPTIONAL MATCH (variable)-[:WAS_GENERATED_BY_VAR]->(variable_activity:ExtractionActivity)
            RETURN e AS evidence,
                   collect(DISTINCT activity) AS evidence_activities,
                   variable,
                   collect(DISTINCT variable_activity) AS variable_activities
            """
        ).strip()
        return Query(cypher=cypher, parameters={"evidence_id": evidence_id})

    def vector_search(
        self,
        *,
        index_name: str,
        query_vector: Sequence[float],
        top_k: int = 10,
    ) -> Query:
        """Return a Cypher query that executes a vector similarity search."""

        cypher = textwrap.dedent(
            """
            CALL db.index.vector.queryNodes($index_name, $top_k, $query_vector)
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
            """
        ).strip()
        params: Dict[str, Any] = {
            "index_name": index_name,
            "top_k": top_k,
            "query_vector": list(query_vector),
        }
        return Query(cypher=cypher, parameters=params)
