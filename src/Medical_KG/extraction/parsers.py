"""Parsing utilities for clinical extraction normalisers."""

from __future__ import annotations

import re

CI_PATTERN = re.compile(r"(?P<low>-?\d+(?:\.\d+)?)\s*(?:–|-|to|,)\s*(?P<high>-?\d+(?:\.\d+)?)")
P_VALUE_PATTERN = re.compile(r"p\s*(?P<op><|<=|=)\s*(?P<value>[0-9.]+)", re.I)
COUNT_PATTERN = re.compile(r"(?P<count>\d+)\s*/\s*(?P<denom>\d+)")
AGE_PATTERN = re.compile(r"(?P<gte>\d{1,3})\s*[-–]\s*(?P<lte>\d{1,3})\s*year", re.I)
AGE_SINGLE_PATTERN = re.compile(r"age\s*(?P<op>>=|<=|>|<)\s*(?P<value>\d{1,3})", re.I)
TEMPORAL_PATTERN = re.compile(r"within\s*(?P<value>\d+)\s*(?P<unit>day|week|month|year)s?", re.I)
LAB_PATTERN = re.compile(
    r"(?P<analyte>[A-Za-z0-9 /-]+)\s*(?P<op>>=|<=|>|<)\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z0-9/^.]+)",
    re.I,
)


def parse_confidence_interval(text: str) -> tuple[float | None, float | None]:
    for match in CI_PATTERN.finditer(text):
        low_raw = match.group("low")
        high_raw = match.group("high")
        low = float(low_raw)
        high = float(high_raw)
        if "." in low_raw or "." in high_raw or high <= 5 or low <= 5:
            return low, high
    return None, None


def parse_p_value(text: str) -> str | None:
    match = P_VALUE_PATTERN.search(text)
    if not match:
        return None
    return f"{match.group('op')}{match.group('value')}"


def parse_count(text: str) -> tuple[int | None, int | None]:
    match = COUNT_PATTERN.search(text)
    if not match:
        return None, None
    return int(match.group("count")), int(match.group("denom"))


def parse_age_logic(text: str) -> dict[str, float] | None:
    if match := AGE_PATTERN.search(text):
        return {"gte": float(match.group("gte")), "lte": float(match.group("lte"))}
    if match := AGE_SINGLE_PATTERN.search(text):
        op = match.group("op")
        value = float(match.group("value"))
        if op in {">", ">="}:
            return {"gte": value}
        return {"lte": value}
    return None


def parse_temporal_constraint(text: str) -> dict[str, float] | None:
    match = TEMPORAL_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group("value"))
    unit = match.group("unit").lower()
    unit_days: dict[str, float] = {"day": 1.0, "week": 7.0, "month": 30.0, "year": 365.0}
    return {"op": "<=", "days": value * unit_days.get(unit, 1.0)}


def parse_lab_threshold(text: str) -> dict[str, str | float] | None:
    match = LAB_PATTERN.search(text)
    if not match:
        return None
    return {
        "label": match.group("analyte").strip(),
        "op": match.group("op"),
        "value": float(match.group("value")),
        "unit": match.group("unit").upper(),
    }


def normalise_number(text: str) -> float | None:
    cleaned = text.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


__all__ = [
    "parse_confidence_interval",
    "parse_p_value",
    "parse_count",
    "parse_age_logic",
    "parse_temporal_constraint",
    "parse_lab_threshold",
    "normalise_number",
]
