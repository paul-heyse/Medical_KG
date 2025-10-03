"""Identifier validators for catalog crosswalks."""

from __future__ import annotations

import re
from typing import Callable, Dict

_VERHOEFF_TABLE_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_TABLE_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

_LOINC_PATTERN = re.compile(r"^[0-9]{1,5}-[0-9]$")
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
_GTIN_PATTERN = re.compile(r"^\d{14}$")
_NCT_PATTERN = re.compile(r"^NCT\d{8}$")
_PMID_PATTERN = re.compile(r"^[1-9]\d*$")
_SNOMED_PATTERN = re.compile(r"^\d{6,18}$")


def _verhoeff_check(value: str) -> bool:
    checksum = 0
    reversed_digits = map(int, reversed(value))
    for i, digit in enumerate(reversed_digits):
        checksum = _VERHOEFF_TABLE_D[checksum][_VERHOEFF_TABLE_P[i % 8][digit]]
    return checksum == 0


def is_valid_nct_id(value: str) -> bool:
    """Validate ClinicalTrials.gov identifiers (NCT########)."""

    return bool(_NCT_PATTERN.fullmatch(value))


def is_valid_pmid(value: str) -> bool:
    """Validate PubMed identifiers (numeric)."""

    return bool(_PMID_PATTERN.fullmatch(value))


def is_valid_doi(value: str) -> bool:
    """Validate DOI identifiers (10.xxxx/...)."""

    return bool(_DOI_PATTERN.fullmatch(value))


def is_valid_loinc(value: str) -> bool:
    """Validate LOINC codes (N-N pattern)."""

    return bool(_LOINC_PATTERN.fullmatch(value))


def is_valid_snomed_identifier(value: str) -> bool:
    """Validate SNOMED identifiers using Verhoeff checksum."""

    if not _SNOMED_PATTERN.fullmatch(value):
        return False
    return _verhoeff_check(value)


def is_valid_gtin14(value: str) -> bool:
    """Validate GTIN-14 codes using mod-10 checksum."""

    if not _GTIN_PATTERN.fullmatch(value):
        return False
    total = 0
    for i, digit in enumerate(reversed(value)):
        weight = 3 if i % 2 else 1
        total += int(digit) * weight
    return total % 10 == 0


def is_valid_unii(value: str) -> bool:
    """Validate UNII (10-character alphanumeric excluding O/I)."""

    return bool(re.fullmatch(r"^[A-HJ-NP-Z0-9]{10}$", value))


VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "nct": is_valid_nct_id,
    "pmid": is_valid_pmid,
    "doi": is_valid_doi,
    "loinc": is_valid_loinc,
    "snomed": is_valid_snomed_identifier,
    "gtin14": is_valid_gtin14,
    "unii": is_valid_unii,
}


__all__ = [
    "VALIDATORS",
    "is_valid_doi",
    "is_valid_gtin14",
    "is_valid_loinc",
    "is_valid_nct_id",
    "is_valid_pmid",
    "is_valid_snomed_identifier",
    "is_valid_unii",
]
