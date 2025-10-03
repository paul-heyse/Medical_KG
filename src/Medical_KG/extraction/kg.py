"""Helpers for translating extractions into Neo4j write statements."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable

from Medical_KG.kg.writer import KnowledgeGraphWriter, WriteStatement

from .models import ExtractionEnvelope, ExtractionType


def _span_json(extraction) -> str:
    return json.dumps([span.model_dump() for span in extraction.evidence_spans], sort_keys=True)


def _node_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).hexdigest()[:12]
    return f"{prefix}:{digest}"


def build_kg_statements(
    envelope: ExtractionEnvelope,
    *,
    document_uri: str,
    study_id: str | None = None,
) -> Iterable[WriteStatement]:
    writer = KnowledgeGraphWriter()
    activity_id = _node_id("ExtractionActivity", f"{document_uri}:{envelope.prompt_hash}")
    writer.write_extraction_activity(
        {
            "id": activity_id,
            "model": envelope.model,
            "version": envelope.version,
            "prompt_hash": envelope.prompt_hash,
            "schema_hash": envelope.schema_hash,
            "timestamp": envelope.ts,
        }
    )
    study_ref = study_id or document_uri
    for extraction in envelope.payload:
        base_payload = extraction.model_dump(by_alias=True, exclude_none=True)
        base_id = _node_id(extraction.type.value, json.dumps(base_payload, sort_keys=True))
        if extraction.type == ExtractionType.PICO:
            payload = {
                "id": base_id,
                "population_json": json.dumps(extraction.population),
                "interventions_json": json.dumps(extraction.interventions),
                "comparators_json": json.dumps(extraction.comparators),
                "outcomes_json": json.dumps(extraction.outcomes),
                "timeframe": extraction.timeframe,
                "spans_json": _span_json(extraction),
            }
            writer.write_evidence_variable(payload, document_uri=document_uri)
            writer.link_generated_by("EvidenceVariable", base_id, activity_id)
        elif extraction.type == ExtractionType.EFFECT:
            outcome_id = _node_id("Outcome", extraction.name)
            writer.write_outcome({"id": outcome_id, "name": extraction.name})
            ev_payload = {
                "id": base_id,
                "type": extraction.measure_type,
                "value": extraction.value,
                "ci_low": extraction.ci_low,
                "ci_high": extraction.ci_high,
                "p_value": extraction.p_value,
                "n_total": extraction.n_total,
                "arm_sizes_json": json.dumps(extraction.arm_sizes or []),
                "model": extraction.model,
                "time_unit_ucum": extraction.time_unit_ucum,
                "spans_json": _span_json(extraction),
                "certainty": extraction.confidence,
            }
            writer.write_evidence(
                ev_payload,
                outcome_id=outcome_id,
                variable_id=outcome_id,
                extraction_activity_id=activity_id,
            )
        elif extraction.type == ExtractionType.ADVERSE_EVENT:
            payload = {
                "id": base_id,
                "term": extraction.term,
                "meddra_pt": extraction.meddra_pt,
                "grade": extraction.grade,
                "count": extraction.count,
                "denom": extraction.denom,
                "arm": extraction.arm,
                "serious": extraction.serious,
                "onset_days": extraction.onset_days,
                "spans_json": _span_json(extraction),
            }
            writer.write_adverse_event(payload, study_nct_id=study_ref)
            writer.link_generated_by("AdverseEvent", base_id, activity_id)
        elif extraction.type == ExtractionType.DOSE:
            payload = {
                "id": base_id,
                "label": extraction.drug.label if extraction.drug else extraction.drug_codes[0].display if extraction.drug_codes else None,
                "dose": {
                    "amount": extraction.amount,
                    "unit": extraction.unit,
                    "frequency_per_day": extraction.frequency_per_day,
                    "duration_days": extraction.duration_days,
                },
            }
            writer.write_intervention(payload, arm_id=f"{study_ref}:arm")
            writer.link_generated_by("Intervention", base_id, activity_id)
        elif extraction.type == ExtractionType.ELIGIBILITY:
            payload = {
                "id": base_id,
                "type": extraction.category,
                "logic_json": json.dumps([criterion.logic.model_dump() if criterion.logic else {} for criterion in extraction.criteria]),
                "human_text": "\n".join(criterion.text for criterion in extraction.criteria),
                "spans_json": _span_json(extraction),
            }
            writer.write_eligibility_constraint(payload, study_nct_id=study_ref)
            writer.link_generated_by("EligibilityConstraint", base_id, activity_id)
    return list(writer.statements)


__all__ = ["build_kg_statements"]
