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
    "Concept": "iri",
    "Drug": "rxcui",
    "Device": "udi_di",
}


RELATIONSHIP_ENDPOINTS: Mapping[str, tuple[str, str, str, str]] = {
    "HAS_CHUNK": ("Document", "uri", "Chunk", "id"),
    "MENTIONS": ("Chunk", "id", "Concept", "iri"),
    "HAS_IDENTIFIER": ("Document", "uri", "Identifier", "value"),
    "DESCRIBES": ("Document", "uri", "Study", "nct_id"),
    "HAS_ARM": ("Study", "nct_id", "Arm", "id"),
    "USES_INTERVENTION": ("Arm", "id", "Intervention", "id"),
    "HAS_OUTCOME": ("Study", "nct_id", "Outcome", "id"),
    "REPORTS": ("Study", "nct_id", "Evidence", "id"),
    "DERIVES_FROM": ("Evidence", "id", "EvidenceVariable", "id"),
    "MEASURES": ("Evidence", "id", "Outcome", "id"),
    "HAS_AE": ("Study", "nct_id", "AdverseEvent", "id"),
    "HAS_ELIGIBILITY": ("Study", "nct_id", "EligibilityConstraint", "id"),
    "WAS_GENERATED_BY": ("Evidence", "id", "ExtractionActivity", "id"),
    "WAS_GENERATED_BY_VAR": ("EvidenceVariable", "id", "ExtractionActivity", "id"),
    "WAS_GENERATED_BY_ELIG": ("EligibilityConstraint", "id", "ExtractionActivity", "id"),
    "SAME_AS": ("Concept", "iri", "Concept", "iri"),
    "IS_A": ("Concept", "iri", "Concept", "iri"),
    "SIMILAR_TO": ("Chunk", "id", "Chunk", "id"),
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
        props = dict(payload)
        parameters: Dict[str, Any] = {"props": props}
        if key in props:
            parameters[key] = props[key]
        for alias in ("id", "uri", "nct_id"):
            if alias in props and alias not in parameters:
                parameters[alias] = props[alias]
        cypher = f"MERGE (n:{label} {{{key}: $props.{key}}}) SET n += $props"
        self._statements.append(WriteStatement(cypher=cypher, parameters=parameters))

    def write_document(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("Document", payload)

    def write_chunk(
        self,
        payload: Mapping[str, Any],
        *,
        document_uri: str | None = None,
        order: int | None = None,
    ) -> None:
        data = dict(payload)
        if document_uri and "doc_uri" not in data:
            data["doc_uri"] = document_uri
        self._merge_node("Chunk", data)
        if document_uri:
            params: Dict[str, Any] = {"doc_uri": document_uri, "chunk_id": data["id"]}
            cypher = (
                "MATCH (d:Document {uri: $doc_uri}) MATCH (c:Chunk {id: $chunk_id}) "
                "MERGE (d)-[r:HAS_CHUNK]->(c)"
            )
            if order is not None:
                cypher += " SET r.order = $order"
                params["order"] = order
            self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_concept(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("Concept", payload)

    def write_identifier(self, payload: Mapping[str, Any], *, document_uri: str) -> None:
        scheme = payload.get("scheme")
        value = payload.get("value")
        if not scheme or not value:
            raise ValueError("Identifier payload must include scheme and value")
        cypher = (
            "MERGE (i:Identifier {scheme: $scheme, value: $value}) SET i += $props "
            "WITH i MATCH (d:Document {uri: $doc_uri}) MERGE (d)-[:HAS_IDENTIFIER]->(i)"
        )
        self._statements.append(
            WriteStatement(
                cypher=cypher,
                parameters={"scheme": scheme, "value": value, "doc_uri": document_uri, "props": dict(payload)},
            )
        )

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

    def write_intervention(
        self,
        payload: Mapping[str, Any],
        *,
        arm_id: str,
        dose: Mapping[str, Any] | None = None,
    ) -> None:
        self._merge_node("Intervention", payload)
        cypher = (
            "MATCH (a:Arm {id: $arm_id}) MATCH (i:Intervention {id: $intervention_id}) "
            "MERGE (a)-[r:USES_INTERVENTION]->(i)"
        )
        params: Dict[str, Any] = {"arm_id": arm_id, "intervention_id": payload["id"]}
        if dose:
            cypher += " SET r += $dose"
            params["dose"] = dict(dose)
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_drug(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("Drug", payload)

    def write_device(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("Device", payload)

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

    def write_evidence_variable(
        self,
        payload: Mapping[str, Any],
        *,
        document_uri: str | None = None,
        extraction_activity_id: str | None = None,
    ) -> None:
        self._merge_node("EvidenceVariable", payload)
        if document_uri:
            cypher = (
                "MATCH (d:Document {uri: $doc_uri}) MATCH (ev:EvidenceVariable {id: $ev_id}) "
                "MERGE (d)-[:REPORTS]->(ev)"
            )
            self._statements.append(
                WriteStatement(cypher=cypher, parameters={"doc_uri": document_uri, "ev_id": payload["id"]})
            )
        if extraction_activity_id:
            self.link_generated_by(
                "EvidenceVariable", payload["id"], extraction_activity_id, relationship="WAS_GENERATED_BY_VAR"
            )

    def write_evidence(
        self,
        payload: Mapping[str, Any],
        *,
        outcome_id: str,
        variable_id: str,
        study_nct_id: str | None = None,
        extraction_activity_id: str | None = None,
    ) -> None:
        self._merge_node("Evidence", payload)
        confidence = payload.get("confidence")
        rel_props = {"confidence": confidence} if confidence is not None else {}
        self._statements.append(
            WriteStatement(
                cypher=(
                    "MATCH (e:Evidence {id: $evidence_id}) MATCH (o:Outcome {id: $outcome_id}) "
                    "MERGE (e)-[r:MEASURES]->(o)"
                    + (" SET r += $rel_props" if rel_props else "")
                ),
                parameters={"evidence_id": payload["id"], "outcome_id": outcome_id, "rel_props": rel_props},
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
        if study_nct_id:
            self._statements.append(
                WriteStatement(
                    cypher=(
                        "MATCH (s:Study {nct_id: $nct_id}) MATCH (e:Evidence {id: $evidence_id}) "
                        "MERGE (s)-[:REPORTS]->(e)"
                    ),
                    parameters={"nct_id": study_nct_id, "evidence_id": payload["id"]},
                )
            )
        if extraction_activity_id:
            self.link_generated_by("Evidence", payload["id"], extraction_activity_id)

    def write_adverse_event(
        self,
        payload: Mapping[str, Any],
        *,
        study_nct_id: str,
        arm_id: str | None = None,
    ) -> None:
        self._merge_node("AdverseEvent", payload)
        rel_props: MutableMapping[str, Any] = {}
        for field in ("count", "denominator", "grade"):
            if field in payload:
                rel_props[field] = payload[field]
        cypher = (
            "MATCH (s:Study {nct_id: $nct_id}) MATCH (ae:AdverseEvent {id: $ae_id}) "
            "MERGE (s)-[r:HAS_AE]->(ae)"
            + (" SET r += $rel_props" if rel_props else "")
        )
        params: Dict[str, Any] = {"nct_id": study_nct_id, "ae_id": payload["id"], "rel_props": rel_props}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))
        if arm_id:
            cypher_arm = (
                "MATCH (a:Arm {id: $arm_id}) MATCH (ae:AdverseEvent {id: $ae_id}) "
                "MERGE (a)-[:HAS_AE]->(ae)"
            )
            self._statements.append(
                WriteStatement(cypher=cypher_arm, parameters={"arm_id": arm_id, "ae_id": payload["id"]})
            )

    def write_eligibility_constraint(self, payload: Mapping[str, Any], *, study_nct_id: str) -> None:
        self._merge_node("EligibilityConstraint", payload)
        cypher = (
            "MATCH (s:Study {nct_id: $nct_id}) MATCH (e:EligibilityConstraint {id: $constraint_id}) "
            "MERGE (s)-[:HAS_ELIGIBILITY]->(e)"
        )
        params = {"constraint_id": payload["id"], "nct_id": study_nct_id}
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_extraction_activity(self, payload: Mapping[str, Any]) -> None:
        self._merge_node("ExtractionActivity", payload)

    def link_generated_by(
        self,
        node_label: str,
        node_id: str,
        activity_id: str,
        *,
        relationship: str = "WAS_GENERATED_BY",
    ) -> None:
        key = NODE_KEYS.get(node_label)
        if key is None:
            raise ValueError(f"Unknown node label '{node_label}'")
        cypher = (
            f"MATCH (n:{node_label} {{{key}: $node_key}}) MATCH (a:ExtractionActivity {{id: $activity_id}}) "
            f"MERGE (n)-[:{relationship}]->(a)"
        )
        params = {"node_key": node_id, "activity_id": activity_id}
        if key != "id":
            params[key] = node_id
        self._statements.append(WriteStatement(cypher=cypher, parameters=params))

    def write_relationship(
        self,
        rel_type: str,
        start_value: Any,
        end_value: Any,
        properties: Mapping[str, Any] | None = None,
        *,
        start_label: str | None = None,
        start_key: str | None = None,
        end_label: str | None = None,
        end_key: str | None = None,
    ) -> None:
        if start_label is None:
            start_label = "Document" if rel_type == "HAS_CHUNK" else "Chunk"
        if end_label is None:
            end_label = "Chunk" if rel_type == "HAS_CHUNK" else "Chunk"
        if start_key is None:
            start_key = "id" if rel_type == "HAS_CHUNK" else NODE_KEYS.get(start_label, "id")
        if end_key is None:
            end_key = NODE_KEYS.get(end_label, "id")
        cypher = (
            f"MATCH (start:{start_label} {{{start_key}: $start_value}}) "
            f"MATCH (end:{end_label} {{{end_key}: $end_value}}) "
            f"MERGE (start)-[:{rel_type}]->(end)"
        )
        self._statements.append(
            WriteStatement(
                cypher=cypher,
                parameters={
                    "start_value": start_value,
                    "end_value": end_value,
                },
            )
        )

