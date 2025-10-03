from pathlib import Path

import yaml
from Medical_KG.catalog.licenses import load_license_policy
from Medical_KG.catalog.loaders import SnomedCTLoader
from Medical_KG.catalog.models import Concept, ConceptFamily, Synonym, SynonymType
from Medical_KG.catalog.pipeline import LicensePolicy


def make_concept(license_bucket: str) -> Concept:
    return Concept(
        iri="https://example.org/c/1",
        ontology="SNOMED",
        family=ConceptFamily.CONDITION,
        label="Hypertension",
        preferred_term="Hypertension",
        synonyms=[Synonym(value="High blood pressure", type=SynonymType.RELATED)],
        codes={"snomed": "123"},
        license_bucket=license_bucket,
    )


def test_license_policy_from_file_and_loader_toggle(tmp_path: Path) -> None:
    config_path = tmp_path / "license.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "buckets": {"open": True, "restricted": False},
                "loaders": {"SNOMED": {"enabled": False}},
            }
        ),
        encoding="utf-8",
    )

    policy = LicensePolicy.from_file(config_path)
    loader = SnomedCTLoader(records=[{"conceptId": "1", "fsn": "Condition"}])

    assert not policy.entitlements["restricted"]
    assert not policy.is_loader_enabled(loader)


def test_license_policy_filtering_and_default(tmp_path: Path) -> None:
    concepts = [
        make_concept("open"),
        make_concept("restricted"),
    ]
    public_policy = LicensePolicy.public()
    permissive_policy = load_license_policy(None)
    missing_policy = load_license_policy(tmp_path / "does-not-exist.yaml")

    assert [concept.license_bucket for concept in public_policy.filter_concepts(concepts)] == [
        "open"
    ]
    assert len(permissive_policy.filter_concepts(concepts)) == 2
    assert missing_policy.entitlements == permissive_policy.entitlements
