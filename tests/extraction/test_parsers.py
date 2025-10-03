from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from Medical_KG.extraction.parsers import (
    normalise_number,
    parse_age_logic,
    parse_confidence_interval,
    parse_count,
    parse_lab_threshold,
    parse_p_value,
    parse_temporal_constraint,
)


def test_parse_confidence_interval_prefers_decimal() -> None:
    low, high = parse_confidence_interval("CI 95%: 1.2-3.4 and 12-34")
    assert low == 1.2 and high == 3.4


def test_parse_p_value_handles_lt() -> None:
    assert parse_p_value("p < 0.05") == "<0.05"


def test_parse_count_extracts_values() -> None:
    assert parse_count("Observed 12/50 patients") == (12, 50)


def test_parse_age_logic_handles_single_bound() -> None:
    assert parse_age_logic("age >= 65 years") == {"gte": 65.0}


def test_parse_lab_threshold_returns_ucum() -> None:
    lab = parse_lab_threshold("creatinine > 2.0 mg/dL")
    assert lab == {"label": "creatinine", "op": ">", "value": 2.0, "unit": "MG/DL"}


def test_parse_temporal_constraint_normalises_units() -> None:
    temporal = parse_temporal_constraint("within 6 months of enrollment")
    assert temporal == {"op": "<=", "days": 180.0}


@given(st.integers(min_value=1, max_value=365), st.sampled_from(["day", "week", "month", "year"]), st.booleans())
def test_temporal_constraint_property(value: int, unit: str, plural: bool) -> None:
    suffix = "s" if plural else ""
    text = f"Within {value} {unit}{suffix}"
    result = parse_temporal_constraint(text)
    assert result is not None
    days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
    assert math.isclose(result["days"], value * days, rel_tol=1e-6)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1,234", 1234.0),
        (" 42 ", 42.0),
        ("invalid", None),
    ],
)
def test_normalise_number(raw: str, expected: float | None) -> None:
    assert normalise_number(raw) == expected

