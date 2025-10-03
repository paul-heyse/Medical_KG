from __future__ import annotations

from Medical_KG.extraction.normalizers import (
    normalise_adverse_event,
    normalise_dose,
    normalise_effect,
    normalise_eligibility,
    normalise_pico,
)


def test_normalise_pico_deduplicates_lists(pico_extraction) -> None:
    result = normalise_pico(pico_extraction)

    assert result.interventions == ["metformin"]
    assert result.comparators == ["placebo"]
    assert result.outcomes == ["mortality"]


def test_normalise_effect_parses_ci_and_counts(effect_extraction, clinical_snippets) -> None:
    text = clinical_snippets["effect"]
    result = normalise_effect(effect_extraction, text=text)

    assert result.ci_low == 0.60
    assert result.ci_high == 0.90
    assert result.p_value == "=0.02"
    assert result.arm_sizes == [120]
    assert result.n_total == 240


def test_normalise_adverse_event_filters_codes(ae_extraction, clinical_snippets) -> None:
    text = clinical_snippets["ae"]
    result = normalise_adverse_event(ae_extraction, text=text)

    assert result.codes and result.codes[0].display == "Nausea"
    assert result.serious is True
    assert result.count == 12 and result.denom == 100


def test_normalise_dose_enriches_metadata(dose_extraction, clinical_snippets) -> None:
    text = clinical_snippets["dose"]
    result = normalise_dose(dose_extraction, text=text)

    assert result.drug_codes and result.drug_codes[0].code == "6809"
    assert result.route == "PO"
    assert result.frequency_per_day == 2.0


def test_normalise_eligibility_resolves_logic(eligibility_extraction, clinical_snippets) -> None:
    text = clinical_snippets["eligibility"]
    result = normalise_eligibility(eligibility_extraction, text=text)

    logic = result.criteria[0].logic
    assert logic is not None
    assert logic.age == {"gte": 18.0, "lte": 65.0}

