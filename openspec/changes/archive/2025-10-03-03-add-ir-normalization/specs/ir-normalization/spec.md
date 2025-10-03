# Intermediate Representation Normalization Capability

## ADDED Requirements

### Requirement: JSON Schema Definitions

The system SHALL define strict JSON Schemas for Document, Block, and Table structures with comprehensive validation rules.

#### Scenario: Document schema validation

- **WHEN** creating or updating a Document IR
- **THEN** the system SHALL validate against document.v1.schema.json requiring doc_id, source, uri, language, and blocks[] fields

#### Scenario: Block schema validation

- **WHEN** adding blocks to Document
- **THEN** the system SHALL validate each block against block.v1.schema.json requiring type, text, and offsets fields

#### Scenario: Table schema validation

- **WHEN** including tables in Document
- **THEN** the system SHALL validate against table.v1.schema.json requiring caption, headers[], and rows[][] with consistent column counts

### Requirement: Text Canonicalization

The system SHALL normalize text to UTF-8 NFC Unicode with consistent whitespace handling while preserving original text for span mapping.

#### Scenario: Unicode normalization

- **WHEN** ingesting text with NFKD or mixed normalization forms
- **THEN** the system SHALL convert all text to NFC and store original in raw_text field

#### Scenario: Whitespace collapsing

- **WHEN** text contains multiple consecutive spaces, tabs, or newlines
- **THEN** the system SHALL collapse to single space while preserving paragraph boundaries (double newline)

#### Scenario: Non-UTF8 encoding

- **WHEN** detecting non-UTF-8 encoded text
- **THEN** the system SHALL attempt conversion via chardet and log encoding detection confidence

### Requirement: De-hyphenation

The system SHALL intelligently rejoin hyphenated words split across line breaks using dictionary validation.

#### Scenario: Valid word rejoin

- **WHEN** encountering "treat-\nment" and dictionary confirms "treatment" is valid
- **THEN** the system SHALL rejoin as "treatment" and update span offsets accordingly

#### Scenario: Invalid word preservation

- **WHEN** encountering "re-\nsearch" but dictionary check fails for "research" in medical context
- **THEN** the system SHALL preserve hyphen and keep as separate tokens

#### Scenario: Span offset mapping

- **WHEN** de-hyphenating words
- **THEN** the system SHALL maintain span_map recording original offsets → canonical offsets

### Requirement: Language Detection

The system SHALL detect document language and store ISO 639-1 code for downstream processing.

#### Scenario: English detection

- **WHEN** analyzing medical text in English
- **THEN** the system SHALL detect language="en" with confidence ≥0.95 using fasttext or CLD

#### Scenario: Non-English warning

- **WHEN** detecting language other than English (e.g., "es", "fr")
- **THEN** the system SHALL log warning and set Document.language but continue processing

#### Scenario: Mixed language handling

- **WHEN** document contains multiple languages (e.g., English with Latin terms)
- **THEN** the system SHALL detect primary language (≥70% of content) and set Document.language accordingly

### Requirement: Span Mapping Preservation

The system SHALL maintain bidirectional span mapping between raw and canonical text for provenance.

#### Scenario: Create span map

- **WHEN** performing normalization transformations
- **THEN** the system SHALL create span_map[] with entries {raw_start, raw_end, canonical_start, canonical_end, transform_type}

#### Scenario: Query raw offsets

- **WHEN** given canonical span (start=100, end=150)
- **THEN** the system SHALL return corresponding raw span using span_map inverse lookup

#### Scenario: Preserve raw text

- **WHEN** storing Document IR
- **THEN** the system SHALL include raw_text field alongside canonical text for debugging

### Requirement: Block Type Classification

The system SHALL classify blocks into types (paragraph, heading, list_item, table, figure_caption, code) for downstream routing.

#### Scenario: Heading detection

- **WHEN** block starts with "Introduction", "Methods", "Results", or "Discussion" and is <100 chars
- **THEN** the system SHALL set block.type="heading" and block.meta.heading_level

#### Scenario: List item detection

- **WHEN** block starts with bullet point, number, or letter followed by punctuation
- **THEN** the system SHALL set block.type="list_item" and extract item marker

#### Scenario: Table caption detection

- **WHEN** block immediately precedes table and starts with "Table N:" pattern
- **THEN** the system SHALL set block.type="table_caption" and link to table via block.meta.table_ref

### Requirement: IMRaD Section Tagging

The system SHALL tag blocks with IMRaD section labels for medical articles.

#### Scenario: Section boundary detection

- **WHEN** encountering heading "Methods" or "Materials and Methods"
- **THEN** the system SHALL tag subsequent blocks with section="methods" until next section heading

#### Scenario: Registry section tagging

- **WHEN** processing ClinicalTrials.gov study
- **THEN** the system SHALL tag blocks with section="eligibility", "arms", "outcomes", or "adverse_events" based on structured fields

#### Scenario: SPL LOINC section tagging

- **WHEN** processing DailyMed SPL with LOINC section codes
- **THEN** the system SHALL tag blocks with section_loinc (e.g., "34067-9" for Indications and Usage)

### Requirement: Reference Normalization

The system SHALL normalize citations to DOI, PMID, or PMCID when identifiable.

#### Scenario: DOI extraction

- **WHEN** text contains "doi:10.1000/xyz" or "<https://doi.org/10.1000/xyz>"
- **THEN** the system SHALL extract DOI and store in block.meta.references[]

#### Scenario: PMID extraction

- **WHEN** text contains "PMID: 12345678" or "PubMed ID 12345678"
- **THEN** the system SHALL extract PMID and store in block.meta.references[]

#### Scenario: Citation linking

- **WHEN** references are extracted
- **THEN** the system SHALL create citation_map[] linking in-text citation markers to reference identifiers

### Requirement: Validation and Quality Checks

The system SHALL validate IR integrity and reject documents failing quality thresholds.

#### Scenario: Required field validation

- **WHEN** Document is missing doc_id, source, or language
- **THEN** the system SHALL reject with ValidationError listing missing fields

#### Scenario: Span offset validation

- **WHEN** block.start or block.end exceed len(Document.text)
- **THEN** the system SHALL reject with ValidationError "Invalid span offsets"

#### Scenario: Block ordering validation

- **WHEN** blocks are not in ascending start offset order
- **THEN** the system SHALL sort blocks by start offset and log warning

### Requirement: IR Storage and Retrieval

The system SHALL store normalized IR in object store with versioning and enable efficient retrieval.

#### Scenario: Write IR to object store

- **WHEN** normalization completes successfully
- **THEN** the system SHALL write JSON to s3://medkg-{env}-ir/{source}/{doc_id}.json with gzip compression

#### Scenario: IR versioning

- **WHEN** re-ingesting document with same ID but different content
- **THEN** the system SHALL compute content hash and store as new version with suffix doc_id#v{timestamp}

#### Scenario: Retrieve IR by doc_id

- **WHEN** downstream service requests IR for doc_id
- **THEN** the system SHALL return parsed Document object from cache or object store
