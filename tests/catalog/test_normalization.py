from Medical_KG.catalog.models import Concept, ConceptFamily, Synonym, SynonymType
from Medical_KG.catalog.normalization import (
    ConceptNormaliser,
    merge_synonym_catalogs,
    normalize_greek,
    normalize_spelling,
    normalize_text,
    recognise_salts,
)


def test_text_normalization_variants() -> None:
    assert normalize_text("  Example  text\n") == "Example text"
    assert normalize_greek("β-blocker") == "beta-blocker"
    assert normalize_spelling("paediatric tumour") == "pediatric tumor"
    assert recognise_salts("Metoprolol sodium") == "Metoprolol (sodium)"


def test_concept_normaliser_deduplicates_synonyms() -> None:
    concept = Concept(
        iri="https://example.org/c/1",
        ontology="RXNORM",
        family=ConceptFamily.DRUG,
        label="Metoprolol",
        preferred_term="Metoprolol",
        synonyms=[
            Synonym(value="Metoprolol", type=SynonymType.EXACT),
            Synonym(value="metoprolol", type=SynonymType.EXACT),
            Synonym(value="β-blocker", type=SynonymType.RELATED),
        ],
        codes={"rxnorm": "123"},
    )
    normaliser = ConceptNormaliser()

    normalised = normaliser.normalise(concept)

    assert [syn.value for syn in normalised.synonyms] == [
        "metoprolol",
        "beta-blocker",
    ]

    catalog = normaliser.aggregate_synonyms([normalised])
    assert catalog["RXNORM"] == ["beta-blocker", "metoprolol"]

    merged = merge_synonym_catalogs(catalog, {"RXNORM": ["Metoprolol"]})
    assert merged["RXNORM"] == ["Metoprolol", "beta-blocker", "metoprolol"]
