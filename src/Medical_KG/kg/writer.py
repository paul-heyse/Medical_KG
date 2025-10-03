from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping


@dataclass(slots=True)
class WriteStatement:
    cypher: str
    parameters: Dict[str, Any]


NODE_KEYS: Mapping[str, str] = {
    "Document": "uri",
    "Chunk": "id",
    "Study": "nct_id",
    "Arm": "id",
    "Intervention": "id",
    "Outcome": "id",
    "EvidenceVariable": "id",
    "Evidence": "id",
    "AdverseEvent": "id",
    "EligibilityConstraint": "id",
    "ExtractionActivity": "id",
}


class KnowledgeGraphWriter:
    """Generates idempotent Cypher statements for Neo4j upserts."""

    def __init__(self) -> None:
        self._statements: list[WriteStatement] = []

    @property
    def statements(self) -> Iterable[WriteStatement]:
        return list(self._statements)

    def clear(self) -> None:
        self._statements.clear()

    def _merge_node(self, label: str, payload: Mapping[str, Any]) -> None:
        key = NODE_KEYS.get(label)
        if key is None:
            raise ValueError(f"Unknown node label '{label}'")
        if key not in payload:
            raise ValueError(f"Payload for {label} missing key '{key}'")
        cypher = f"MERGE (n:{label} {{{key}: $props.{key}}}) SET n += $props"
        self._statements.append(WriteStatement(cypher=cypher, parameters={"props": dict(payload)}))

    def write_document(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("Document", payload)

    def write_chunk(self, payload: Mapping[str, Any], *, document_uri: str | None = None, order: int | None = None) -> None:
        self._merge_node("Chunk", payload)
        if document_uri:
            params: Dict[str, Any] = {"doc_uri": document_uri, "chunk_id": payload["id"]}
            cypher = (
                "MATCH (d:Document {uri: $doc_uri}) MATCH (c:Chunk {id: $chunk_id}) "
                "MERGE (d)-[r:HAS_CHUNK]->(c)"
            )
            if order is not None:
                cypher += " SET r.order = $order"
                params["order"] = order
            self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_study(self, payload: Mapping[str, Any], *, document_uri: str | None = None) -> None:
        self._merge_node("Study", payload)
        if document_uri:
            cypher = (
                "MATCH (d:Document {uri: $doc_uri}) MATCH (s:Study {nct_id: $nct_id}) "
                "MERGE (d)-[:DESCRIBES]->(s)"
            )
            self._statements.append(
                WriteStatement(cypher=cypher, parameters={"doc_uri": document_uri, "nct_id": payload["nct_id"]})
            )

    def write_arm(self, payload: Mapping[str, Any], *, study_nct_id: str) -> None:
        self._merge_node("Arm", payload)
        cypher = (
            "MATCH (s:Study {nct_id: $nct_id}) MATCH (a:Arm {id: $arm_id}) "
            "MERGE (s)-[:HAS_ARM]->(a)"
        )
        params = {"nct_id": study_nct_id, "arm_id": payload["id"]}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_intervention(self, payload: Mapping[str, Any], *, arm_id: str) -> None:
        self._merge_node("Intervention", payload)
        cypher = (
            "MATCH (a:Arm {id: $arm_id}) MATCH (i:Intervention {id: $intervention_id}) "
            "MERGE (a)-[r:USES_INTERVENTION]->(i) SET r += $rel_props"
        )
        rel_props = {key: payload[key] for key in ("dose",) if key in payload}
        params = {"arm_id": arm_id, "intervention_id": payload["id"], "rel_props": rel_props}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_outcome(self, payload: Mapping[str, Any], *, study_nct_id: str | None = None) -> None:
        self._merge_node("Outcome", payload)
        if study_nct_id:
            cypher = (
                "MATCH (s:Study {nct_id: $nct_id}) MATCH (o:Outcome {id: $outcome_id}) "
                "MERGE (s)-[:HAS_OUTCOME]->(o)"
            )
            self._statements.append(
                WriteStatement(cypher=cypher, parameters={"nct_id": study_nct_id, "outcome_id": payload["id"]})
            )

    def write_evidence_variable(self, payload: Mapping[str, Any], *, document_uri: str | None = None) -> None:
        self._merge_node("EvidenceVariable", payload)
        if document_uri:
            cypher = (
                "MATCH (ev:EvidenceVariable {id: $ev_id}) MATCH (d:Document {uri: $doc_uri}) "
                "MERGE (ev)-[:REPORTS]->(d)"
            )
            self._statements.append(
                WriteStatement(cypher=cypher, parameters={"ev_id": payload["id"], "doc_uri": document_uri})
            )

    def write_evidence(
        self,
        payload: Mapping[str, Any],
        *,
        outcome_id: str,
        variable_id: str,
        extraction_activity_id: str | None = None,
    ) -> None:
        self._merge_node("Evidence", payload)
        self._statements.append(
            WriteStatement(
                cypher=(
                    "MATCH (e:Evidence {id: $evidence_id}) MATCH (o:Outcome {id: $outcome_id}) "
                    "MERGE (e)-[r:MEASURES]->(o) SET r += $rel_props"
                ),
                parameters={
                    "evidence_id": payload["id"],
                    "outcome_id": outcome_id,
                    "rel_props": (
                        {"confidence": payload["confidence"]}
                        if payload.get("confidence") is not None
                        else {}
                    ),
                },
            )
        )
        self._statements.append(
            WriteStatement(
                cypher=(
                    "MATCH (e:Evidence {id: $evidence_id}) MATCH (v:EvidenceVariable {id: $variable_id}) "
                    "MERGE (e)-[:DERIVES_FROM]->(v)"
                ),
                parameters={"evidence_id": payload["id"], "variable_id": variable_id},
            )
        )
        if extraction_activity_id:
            self.link_generated_by("Evidence", payload["id"], extraction_activity_id)

    def write_adverse_event(self, payload: Mapping[str, Any], *, study_nct_id: str) -> None:
        self._merge_node("AdverseEvent", payload)
        rel_props: MutableMapping[str, Any] = {}
        for field in ("count", "denominator", "grade"):
            if field in payload:
                rel_props[field] = payload[field]
        cypher = (
            "MATCH (s:Study {nct_id: $nct_id}) MATCH (ae:AdverseEvent {id: $ae_id}) "
            "MERGE (s)-[r:HAS_AE]->(ae) SET r += $rel_props"
        )
        params = {"nct_id": study_nct_id, "ae_id": payload["id"], "rel_props": rel_props}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_eligibility_constraint(self, payload: Mapping[str, Any], *, study_nct_id: str) -> None:
        self._merge_node("EligibilityConstraint", payload)
        cypher = (
            "MATCH (e:EligibilityConstraint {id: $constraint_id}) MATCH (s:Study {nct_id: $nct_id}) "
            "MERGE (e)-[:SATISFIES]->(s)"
        )
        params = {"constraint_id": payload["id"], "nct_id": study_nct_id}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_extraction_activity(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("ExtractionActivity", payload)

    def link_generated_by(self, node_label: str, node_id: str, activity_id: str) -> None:
        key = NODE_KEYS.get(node_label)
        if key is None:
            raise ValueError(f"Unknown node label '{node_label}'")
        cypher = (
            f"MATCH (n:{node_label} {{{key}: $node_id}}) MATCH (a:ExtractionActivity {{id: $activity_id}}) "
            "MERGE (n)-[:WAS_GENERATED_BY]->(a)"
        )
        self._statements.append(WriteStatement(cypher=cypher, parameters={"node_id": node_id, "activity_id": activity_id}))

    def write_relationship(
        self,
        rel_type: str,
        *,
        start_label: str,
        start_key: str,
        start_value: Any,
        end_label: str,
        end_key: str,
        end_value: Any,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        cypher = (
            f"MATCH (a:{start_label} {{{start_key}: $start_val}}) MATCH (b:{end_label} {{{end_key}: $end_val}}) "
            f"MERGE (a)-[r:{rel_type}]->(b)"
        )
        params: Dict[str, Any] = {"start_val": start_value, "end_val": end_value}
        if properties:
            cypher += " SET r += $props"
            params["props"] = dict(properties)
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))
