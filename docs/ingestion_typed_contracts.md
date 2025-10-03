# Ingestion TypedDict Contracts Guide

This guide explains how to work with TypedDict payload contracts when creating or modifying ingestion adapters in the Medical_KG system.

## Table of Contents

- [Overview](#overview)
- [TypedDict Basics](#typeddict-basics)
- [Mixin Patterns](#mixin-patterns)
- [NotRequired Fields](#notrequired-fields)
- [Type Guards](#type-guards)
- [Complete Adapter Examples](#complete-adapter-examples)
  - [Terminology Adapter (UMLS)](#terminology-adapter-umls)
  - [Literature Adapter (PubMed)](#literature-adapter-pubmed)
  - [Clinical Adapter (ClinicalTrials)](#clinical-adapter-clinicaltrials)
- [Migration Guide](#migration-guide)
- [Troubleshooting](#troubleshooting)

## Overview

The ingestion system uses TypedDict to define structured payload contracts for every adapter. This provides:

- **Compile-time type safety**: Catch field typos and type mismatches before runtime
- **IDE autocomplete**: Get intelligent suggestions for payload fields
- **Self-documenting code**: Payload structure is clear from type definitions
- **Refactoring confidence**: Safe renames and structural changes

All TypedDict definitions live in `src/Medical_KG/ingestion/types.py`.

## TypedDict Basics

### What is a TypedDict?

A TypedDict is a dictionary with a fixed set of keys, where each key has a specific type:

```python
from typing import TypedDict

class PersonPayload(TypedDict):
    name: str
    age: int
    email: str
```

This is similar to a dataclass but stays as a plain `dict` at runtime, making it ideal for JSON API payloads.

### Why Not Just Use `dict[str, Any]`?

```python
# ❌ Weak typing - no safety
raw: dict[str, Any] = api_response
title = raw["titel"]  # Typo! Runtime KeyError

# ✅ Strong typing - caught by mypy
raw: PubMedDocumentPayload = construct_payload(api_response)
title = raw["titel"]  # mypy error: Key "titel" not in PubMedDocumentPayload
title = raw["title"]  # ✓ Correct
```

### Defining Adapter Payloads

Each adapter should have a corresponding TypedDict in `types.py`:

```python
# In src/Medical_KG/ingestion/types.py

class MyAdapterPayload(TypedDict):
    """Payload structure for MyAdapter.

    Fields correspond to the JSON structure returned by the MyAPI endpoint.
    """
    id: str
    title: str
    content: str
    metadata: JSONMapping  # Nested JSON object
    tags: Sequence[str]    # JSON array
```

## Mixin Patterns

### Common Field Mixins

Many adapters share common fields. Use mixin TypedDicts to avoid repetition:

```python
class IdentifierMixin(TypedDict):
    """Shared identifier field for payloads that expose a canonical id."""
    identifier: str

class VersionMixin(TypedDict):
    """Shared version metadata for payload revisions."""
    version: str

class TitleMixin(TypedDict):
    """Shared human-readable title for document-centric payloads."""
    title: str

# Compose with multiple inheritance
class MyPayload(TitleMixin, VersionMixin):
    """Inherits both 'title' and 'version' fields."""
    content: str
```

### Available Mixins

The system provides these reusable mixins:

| Mixin | Fields | Use Case |
|-------|--------|----------|
| `IdentifierMixin` | `identifier: str` | Canonical IDs (UMLS CUI, LOINC codes) |
| `VersionMixin` | `version: str` | Versioned resources |
| `TitleMixin` | `title: str` | Document titles |
| `SummaryMixin` | `summary: str` | Guideline summaries |
| `RecordMixin` | `record: JSONMapping` | Wrapper payloads around arbitrary JSON |

### When to Create a New Mixin

Create a mixin if:

- ≥3 adapters share the exact same field(s)
- The field has consistent semantics across adapters
- You want to ensure consistency

Example:

```python
# DON'T: Create mixin for rarely-used field
class ObscureFieldMixin(TypedDict):
    obscure_field: str  # Only 1 adapter uses this

# DO: Inline the field
class MyPayload(TypedDict):
    obscure_field: str
    other_field: int
```

## NotRequired Fields

### When to Use NotRequired

Use `NotRequired` for fields that may be absent from API responses:

```python
from typing import NotRequired

class DocumentPayload(TypedDict):
    id: str                        # Always present
    title: str                     # Always present
    abstract: NotRequired[str]     # May be absent
    doi: NotRequired[str | None]   # May be absent OR null
```

### NotRequired vs Optional

```python
# NotRequired: Key may not exist
abstract: NotRequired[str]          # OK: {"id": "1", "title": "..."}
                                    # OK: {"id": "1", "title": "...", "abstract": "..."}

# NotRequired with None: Key may not exist OR may be null
doi: NotRequired[str | None]        # OK: {"id": "1"}
                                    # OK: {"id": "1", "doi": "10.1234/..."}
                                    # OK: {"id": "1", "doi": null}

# Required but nullable: Key MUST exist, value can be None
status: str | None                  # ERROR: {"id": "1"}  # Missing 'status'
                                    # OK: {"id": "1", "status": null}
                                    # OK: {"id": "1", "status": "active"}
```

### Accessing NotRequired Fields Safely

```python
def parse(self, raw: MyPayload) -> Document:
    # Use .get() for NotRequired fields
    abstract = raw.get("abstract", "")  # Default to empty string
    doi = raw.get("doi")                # Returns None if absent

    # Required fields can be accessed directly
    doc_id = raw["id"]                  # Safe - field is required
    title = raw["title"]                # Safe - field is required

    return Document(
        doc_id=doc_id,
        source="my-source",
        content=f"{title}\n\n{abstract}",
        metadata={"doi": doi} if doi else {},
        raw=raw,
    )
```

### Conventions for NotRequired

1. **API uncertainty**: If the API docs say "optional", use `NotRequired`
2. **Historical data**: Older records may lack newer fields → `NotRequired`
3. **Conditional fields**: Fields that only appear in certain contexts → `NotRequired`
4. **Error states**: Fields that may be omitted during errors → `NotRequired`

## Type Guards

### What Are Type Guards?

Type guards narrow union types to specific alternatives, enabling static type checking:

```python
from typing import TypeGuard

def is_pubmed_payload(raw: DocumentRaw | None) -> TypeGuard[PubMedDocumentPayload]:
    """Check if raw payload is a PubMed document."""
    return isinstance(raw, dict) and "pmid" in raw

# Usage in adapter
def validate(self, document: Document) -> None:
    raw = document.raw
    if not is_pubmed_payload(raw):
        raise ValueError("PubMedAdapter produced non-PubMed payload")

    # After guard, mypy knows raw is PubMedDocumentPayload
    pmid = raw["pmid"]  # ✓ Type-safe access
```

### Available Type Guards

The `types.py` module provides family-level guards:

```python
# Payload family guards
is_terminology_payload(raw) -> TypeGuard[TerminologyDocumentPayload]
is_literature_payload(raw) -> TypeGuard[LiteratureDocumentPayload]
is_clinical_payload(raw) -> TypeGuard[ClinicalCatalogDocumentPayload]
is_guideline_payload(raw) -> TypeGuard[GuidelineDocumentPayload]

# Adapter-specific guards
is_pubmed_payload(raw) -> TypeGuard[PubMedDocumentPayload]
is_pmc_payload(raw) -> TypeGuard[PmcDocumentPayload]
is_mesh_payload(raw) -> TypeGuard[MeshDocumentPayload]
# ... (see types.py for complete list)
```

### When to Use Type Guards

Use type guards in:

1. **validate() methods**: Ensure adapter produced correct payload shape
2. **Conditional logic**: When processing different payload families
3. **Error handling**: Provide clear error messages for wrong payload types

```python
# Example: validate() method
def validate(self, document: Document) -> None:
    raw = document.raw
    assert is_umls_payload(raw), "UMLSAdapter produced non-UMLS payload"

    # Now safe to access UMLS-specific fields
    if not raw["cui"].startswith("C"):
        raise ValueError(f"Invalid CUI format: {raw['cui']}")
```

## Complete Adapter Examples

### Terminology Adapter (UMLS)

This example shows a complete terminology adapter with typed payloads:

```python
# In src/Medical_KG/ingestion/types.py
class UmlsDocumentPayload(IdentifierMixin, TitleMixin):
    """UMLS Metathesaurus concept payload."""
    cui: str
    semantic_types: Sequence[str]
    atoms: Sequence[JSONMapping]
    definitions: NotRequired[Sequence[str]]  # Not all concepts have definitions
    relations: NotRequired[Sequence[JSONMapping]]  # May be absent

# In src/Medical_KG/ingestion/adapters/terminology.py
from typing import Any, AsyncIterator, Sequence, cast

from Medical_KG.ingestion.types import (
    JSONMapping,
    UmlsDocumentPayload,
    is_umls_payload,
)

class UMLSAdapter(HttpAdapter[UmlsDocumentPayload]):
    """UMLS Metathesaurus ingestion adapter."""

    async def fetch(self) -> AsyncIterator[Any]:
        """Fetch raw API responses (untyped JSON)."""
        async for concept_id in self._iter_concept_ids():
            url = f"{self.base_url}/content/current/CUI/{concept_id}"
            response = await self.client.get_json(url)
            yield cast(JSONMapping, response.data)

    def parse(self, raw: Any) -> Document:
        """Transform raw API response into typed payload and Document."""
        # Construct typed payload
        payload: UmlsDocumentPayload = {
            "identifier": raw["ui"],
            "cui": raw["ui"],
            "title": raw.get("name", ""),
            "semantic_types": [st["name"] for st in raw.get("semanticTypes", [])],
            "atoms": raw.get("atoms", []),
        }

        # Add optional fields if present
        if definitions := raw.get("definitions"):
            payload["definitions"] = [d["value"] for d in definitions]
        if relations := raw.get("relations"):
            payload["relations"] = relations

        # Build content text
        content_parts = [payload["title"]]
        if defs := payload.get("definitions"):
            content_parts.extend(defs)

        return Document(
            doc_id=f"umls:{payload['cui']}",
            source="umls",
            content="\n\n".join(content_parts),
            metadata={
                "cui": payload["cui"],
                "semantic_types": list(payload["semantic_types"]),
            },
            raw=payload,  # Type-safe: mypy validates this is UmlsDocumentPayload
        )

    def validate(self, document: Document) -> None:
        """Validate document has well-formed UMLS payload."""
        raw = document.raw
        assert is_umls_payload(raw), "UMLSAdapter produced non-UMLS payload"

        # Validate CUI format
        if not raw["cui"].startswith("C"):
            raise ValueError(f"Invalid CUI format: {raw['cui']}")

        # Validate content matches title
        if not document.content.startswith(raw["title"]):
            raise ValueError("Document content doesn't start with title")
```

### Literature Adapter (PubMed)

Complete example for literature ingestion:

```python
# In src/Medical_KG/ingestion/types.py
class PubMedDocumentPayload(TitleMixin):
    """PubMed article payload."""
    pmid: str
    abstract: NotRequired[str]  # Some articles lack abstracts
    authors: Sequence[str]
    journal: str
    pub_date: NotRequired[str]  # Historical records may lack dates
    doi: NotRequired[str | None]  # Can be absent or null
    mesh_terms: NotRequired[Sequence[str]]
    keywords: NotRequired[Sequence[str]]

# In src/Medical_KG/ingestion/adapters/literature.py
from typing import Any, AsyncIterator, Mapping, Sequence, TypedDict, cast

from Medical_KG.ingestion.types import (
    JSONMapping,
    PubMedDocumentPayload,
    is_pubmed_payload,
)


class PubMedSummaryEnvelope(TypedDict):
    result: Mapping[str, JSONMapping]
    uids: Sequence[str]


class PubMedAdapter(HttpAdapter[PubMedDocumentPayload]):
    """PubMed article ingestion adapter."""

    async def fetch(self) -> AsyncIterator[Any]:
        """Fetch article summaries from E-utilities API."""
        async for pmid in self._iter_pmids():
            url = f"{self.base_url}/esummary.fcgi"
            response = await self.client.get_json(url, params={"id": pmid})
            payload = cast(PubMedSummaryEnvelope, response.data)
            yield payload["result"][pmid]

    def parse(self, raw: Any) -> Document:
        """Parse PubMed API response into typed payload."""
        # Extract authors
        authors = []
        for author_data in raw.get("authors", []):
            if name := author_data.get("name"):
                authors.append(name)

        # Construct typed payload
        payload: PubMedDocumentPayload = {
            "pmid": str(raw["uid"]),
            "title": raw.get("title", ""),
            "authors": authors,
            "journal": raw.get("fulljournalname", "Unknown"),
        }

        # Add optional fields
        if abstract := raw.get("abstract"):
            payload["abstract"] = abstract
        if pub_date := raw.get("pubdate"):
            payload["pub_date"] = pub_date
        if doi := raw.get("elocationid"):
            payload["doi"] = doi if doi else None
        if mesh := raw.get("meshterms"):
            payload["mesh_terms"] = mesh

        # Build content
        content = payload["title"]
        if abstract := payload.get("abstract"):
            content += f"\n\n{abstract}"

        return Document(
            doc_id=f"pubmed:{payload['pmid']}",
            source="pubmed",
            content=content,
            metadata={
                "pmid": payload["pmid"],
                "authors": list(payload["authors"]),
                "journal": payload["journal"],
                "pub_date": payload.get("pub_date"),
            },
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        """Validate PubMed document structure."""
        raw = document.raw
        assert is_pubmed_payload(raw), "PubMedAdapter produced non-PubMed payload"

        # Validate PMID format (numeric)
        if not raw["pmid"].isdigit():
            raise ValueError(f"Invalid PMID: {raw['pmid']}")

        # Validate DOI format if present
        if doi := raw.get("doi"):
            if not doi.startswith("10."):
                raise ValueError(f"Invalid DOI format: {doi}")
```

### Clinical Adapter (ClinicalTrials)

Complete example for clinical trial ingestion:

```python
# In src/Medical_KG/ingestion/types.py
class ClinicalTrialsStudyPayload(TypedDict):
    """ClinicalTrials.gov study payload (API v2 format)."""
    protocolSection: JSONMapping
    derivedSection: NotRequired[JSONMapping]  # Computed fields, may be absent

class ClinicalDocumentPayload(TitleMixin, VersionMixin):
    """Structured clinical trial document."""
    nct_id: str
    arms: Sequence[JSONMapping]
    eligibility: JSONValue
    status: NotRequired[str | None]
    phase: NotRequired[str | None]
    study_type: NotRequired[str | None]
    lead_sponsor: NotRequired[str | None]
    enrollment: NotRequired[int | str | None]
    start_date: NotRequired[str | None]
    completion_date: NotRequired[str | None]

# In src/Medical_KG/ingestion/adapters/clinical.py
from typing import Any, AsyncIterator, cast

from Medical_KG.ingestion.types import (
    ClinicalDocumentPayload,
    ClinicalTrialsStudyPayload,
    JSONMapping,
    is_clinical_document_payload,
)


class ClinicalTrialsGovAdapter(HttpAdapter[ClinicalTrialsStudyPayload]):
    """ClinicalTrials.gov API v2 adapter."""

    async def fetch(self) -> AsyncIterator[Any]:
        """Fetch study records from API v2."""
        async for nct_id in self._iter_nct_ids():
            url = f"{self.base_url}/studies/{nct_id}"
            response = await self.client.get_json(url)
            yield cast(JSONMapping, response.data)

    def parse(self, raw: Any) -> Document:
        """Parse API v2 study into structured document payload."""
        protocol = raw["protocolSection"]
        identification = protocol.get("identificationModule", {})
        design = protocol.get("designModule", {})
        arms_module = protocol.get("armsInterventionsModule", {})
        eligibility_module = protocol.get("eligibilityModule", {})
        status_module = protocol.get("statusModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

        # Construct payload
        payload: ClinicalDocumentPayload = {
            "nct_id": identification.get("nctId", ""),
            "title": identification.get("officialTitle", identification.get("briefTitle", "")),
            "version": status_module.get("lastUpdatePostDateStruct", {}).get("date", ""),
            "arms": arms_module.get("armGroups", []),
            "eligibility": eligibility_module,
        }

        # Add optional fields
        if status := status_module.get("overallStatus"):
            payload["status"] = status
        if phases := design.get("phases"):
            payload["phase"] = ", ".join(phases) if isinstance(phases, list) else phases
        if study_type := design.get("studyType"):
            payload["study_type"] = study_type
        if lead := sponsor_module.get("leadSponsor", {}).get("name"):
            payload["lead_sponsor"] = lead
        if enrollment := design.get("enrollmentInfo", {}).get("count"):
            payload["enrollment"] = enrollment
        if start := status_module.get("startDateStruct", {}).get("date"):
            payload["start_date"] = start
        if completion := status_module.get("completionDateStruct", {}).get("date"):
            payload["completion_date"] = completion

        # Build content from title and eligibility
        content = payload["title"]
        if criteria := eligibility_module.get("eligibilityCriteria"):
            content += f"\n\nEligibility:\n{criteria}"

        return Document(
            doc_id=f"clinicaltrials:{payload['nct_id']}",
            source="clinicaltrials.gov",
            content=content,
            metadata={
                "nct_id": payload["nct_id"],
                "status": payload.get("status"),
                "phase": payload.get("phase"),
            },
            raw=raw,  # Store original API response
        )

    def validate(self, document: Document) -> None:
        """Validate clinical trial document."""
        raw = document.raw
        assert is_clinical_document_payload(raw), "ClinicalTrialsGov adapter produced wrong payload"

        # Validate NCT ID format
        if not raw["protocolSection"].get("identificationModule", {}).get("nctId", "").startswith("NCT"):
            raise ValueError("Invalid NCT ID format")
```

## Migration Guide

### Converting Existing Any-Typed Adapters

Follow these steps to migrate an adapter from `Any` to TypedDict:

#### Step 1: Define the TypedDict

Analyze API responses and define the payload structure:

```python
# Before: adapter uses Any
class MyAdapter(HttpAdapter[Any]):
    pass

# After: define TypedDict in types.py
class MyAdapterPayload(TypedDict):
    id: str
    name: str
    data: JSONMapping
    optional_field: NotRequired[str]

# Update adapter
class MyAdapter(HttpAdapter[MyAdapterPayload]):
    pass
```

#### Step 2: Update parse() Signature

Change `parse()` to accept and return typed payload:

```python
# Before
def parse(self, raw: Any) -> Document:
    doc_id = raw["id"]  # Untyped access
    return Document(doc_id=doc_id, ...)

# After
def parse(self, raw: Any) -> Document:
    # Construct typed payload
    payload: MyAdapterPayload = {
        "id": raw["id"],
        "name": raw["name"],
        "data": raw.get("data", {}),
    }
    if optional := raw.get("optional_field"):
        payload["optional_field"] = optional

    return Document(
        doc_id=payload["id"],
        ...,
        raw=payload,  # Store typed payload
    )
```

#### Step 3: Update validate() with Type Guards

Add type guard for safe validation:

```python
# Before
def validate(self, document: Document) -> None:
    if isinstance(document.raw, dict):
        doc_id = document.raw.get("id")
        # ...

# After
def validate(self, document: Document) -> None:
    raw = document.raw
    assert is_my_adapter_payload(raw), "MyAdapter produced wrong payload"

    # Type-safe access
    doc_id = raw["id"]
    # ...
```

#### Step 4: Run mypy and Fix Errors

```bash
mypy --strict src/Medical_KG/ingestion/adapters/my_adapter.py
```

Common errors and fixes:

```python
# Error: "Dict" has no attribute "some_field"
# Fix: Add field to TypedDict or use .get()

# Error: Key "typo" not in MyPayload
# Fix: Correct the typo

# Error: Incompatible type "str | None"; expected "str"
# Fix: Add NotRequired or handle None case
```

## Troubleshooting

### Common Mypy Errors

#### Error: Missing type parameters for generic type

```
error: Missing type parameters for generic type "HttpAdapter"
```

**Fix**: Specify the payload TypedDict:

```python
# Wrong
class MyAdapter(HttpAdapter):
    pass

# Correct
class MyAdapter(HttpAdapter[MyAdapterPayload]):
    pass
```

#### Error: Incompatible type for "raw"

```
error: Argument "raw" to "Document" has incompatible type "dict[str, Any]"; expected "DocumentRaw | None"
```

**Fix**: Construct a proper TypedDict instead of plain dict:

```python
# Wrong
raw_dict = {"id": "123", "name": "test"}
return Document(..., raw=raw_dict)

# Correct
payload: MyAdapterPayload = {
    "id": "123",
    "name": "test",
}
return Document(..., raw=payload)
```

#### Error: TypedDict key must be string literal

```
error: TypedDict key must be a string literal; expected one of ("id", "name", ...)
```

**Fix**: Use literal strings, not variables, for TypedDict keys:

```python
# Wrong
field_name = "id"
value = payload[field_name]  # Can't use variable

# Correct
value = payload["id"]  # Use literal string

# Alternative: Use .get() with variable
value = payload.get(field_name)  # Returns JSONValue | None
```

#### Error: Union attribute access

```
error: Item "None" of "DocumentRaw | None" has no attribute "id"
```

**Fix**: Use type guard or check for None:

```python
# Wrong
doc_id = document.raw["id"]  # raw might be None

# Correct with guard
if is_my_adapter_payload(document.raw):
    doc_id = document.raw["id"]

# Correct with None check
if document.raw is not None and "id" in document.raw:
    doc_id = document.raw["id"]
```

### Testing Typed Adapters

Create fixtures with proper types:

```python
# In tests/ingestion/fixtures/my_adapter.py
from Medical_KG.ingestion.types import MyAdapterPayload

def my_adapter_payload() -> MyAdapterPayload:
    """Fixture with all required fields."""
    return {
        "id": "test-123",
        "name": "Test Document",
        "data": {"key": "value"},
    }

def my_adapter_payload_with_optional() -> MyAdapterPayload:
    """Fixture with optional fields present."""
    return {
        "id": "test-456",
        "name": "Test with Optional",
        "data": {},
        "optional_field": "present",
    }

# In tests/ingestion/test_adapters.py
def test_my_adapter_parse(my_adapter_payload: MyAdapterPayload):
    adapter = MyAdapter(context, client)
    document = adapter.parse(my_adapter_payload)

    # Type-safe assertions
    assert document.doc_id == f"source:{my_adapter_payload['id']}"
    assert isinstance(document.raw, dict)
    assert document.raw["id"] == "test-123"
```

### Performance Considerations

TypedDict has zero runtime overhead - it's only for static type checking. However:

1. **Avoid unnecessary copying**: TypedDicts are still dicts, so copying is expensive
2. **Use views**: For large nested structures, access fields directly rather than copying
3. **Profile if concerned**: Run `pytest --profile` to identify bottlenecks

### Best Practices Summary

✅ **DO**:

- Define TypedDict for every adapter payload
- Use `NotRequired` for optional API fields
- Leverage mixins for common fields
- Write type guards for `validate()` methods
- Test with fixtures for both present and absent optional fields

❌ **DON'T**:

- Use `Any` or `dict[str, Any]` for payloads
- Forget to update `Document.raw` with typed payload
- Access NotRequired fields without `.get()`
- Create TypedDicts with hundreds of fields (split into nested structures)
- Use `# type: ignore` to silence mypy errors (fix the underlying issue)

## Additional Resources

- [Python TypedDict documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/)
- [NotRequired documentation](https://docs.python.org/3/library/typing.html#typing.NotRequired)
- [TypeGuard documentation](https://docs.python.org/3/library/typing.html#typing.TypeGuard)
- Project-specific: `docs/type_safety.md`, `docs/ingestion_runbooks.md`
- Source code: `src/Medical_KG/ingestion/types.py` (all payload definitions)

## Getting Help

- Review existing adapters: `src/Medical_KG/ingestion/adapters/{terminology,literature,clinical}.py`
- Check test fixtures: `tests/ingestion/fixtures/` for payload examples
- Run mypy in strict mode: `mypy --strict src/Medical_KG/ingestion/adapters/your_adapter.py`
- Consult `CONTRIBUTING.md` for code review checklist
