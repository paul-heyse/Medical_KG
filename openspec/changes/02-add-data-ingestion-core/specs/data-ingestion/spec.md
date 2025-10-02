# Data Ingestion Capability

## ADDED Requirements

### Requirement: HTTP Client with Rate Limiting

The system SHALL provide a common HTTP client for all adapters with per-host rate limiting, exponential backoff retries, and timeout configuration.

#### Scenario: Rate limit respected

- **WHEN** an adapter makes requests to NCBI E-utilities without API key
- **THEN** the client SHALL enforce a maximum of 3 requests per second per host

#### Scenario: Retry on transient failure

- **WHEN** a request fails with 429, 502, 503, or 504 status
- **THEN** the client SHALL retry with exponential backoff (max 3 retries) and jitter

#### Scenario: Timeout configuration

- **WHEN** an adapter configures connect_timeout=10s and read_timeout=30s
- **THEN** the client SHALL enforce these timeouts and raise TimeoutError on expiry

### Requirement: Ingestion Ledger

The system SHALL maintain a ledger of document ingestion states to enable idempotent operations and manual PDF processing gates.

#### Scenario: Auto-pipeline document

- **WHEN** a non-PDF source document is ingested
- **THEN** the ledger SHALL record state transitions: auto_inflight → auto_done (or *_failed on error)

#### Scenario: PDF download only

- **WHEN** a PDF document is ingested
- **THEN** the ledger SHALL record state=pdf_downloaded and SHALL NOT trigger automatic chunking/embedding

#### Scenario: Query by state

- **WHEN** querying the ledger for status=pdf_downloaded
- **THEN** the system SHALL return all documents awaiting manual MinerU processing

### Requirement: PubMed E-utilities Adapter

The system SHALL ingest PubMed citations and abstracts via NCBI E-utilities (ESearch, EFetch, ESummary) with API key support and history-based paging.

#### Scenario: Search with history paging

- **WHEN** searching for "sepsis lactate" with usehistory=y and retmax=1000
- **THEN** the adapter SHALL use WebEnv + query_key for paging and retrieve batches of up to 10,000 UIDs

#### Scenario: Metadata extraction

- **WHEN** fetching a PMID
- **THEN** the adapter SHALL extract PMID, PMCID (if linked), DOI, title, abstract, authors, MeSH terms, journal, year, and publication types

#### Scenario: Rate limit with API key

- **WHEN** NCBI_EUTILS_API_KEY is configured
- **THEN** the adapter SHALL allow up to 10 requests per second

### Requirement: PMC OAI-PMH Adapter

The system SHALL harvest full-text open-access articles from PubMed Central via OAI-PMH with JATS XML parsing.

#### Scenario: Harvest by date range

- **WHEN** harvesting from=2025-01-01 to until=2025-01-31 with metadataPrefix=pmc
- **THEN** the adapter SHALL use ListRecords and resumptionToken until exhausted

#### Scenario: JATS XML to IR

- **WHEN** parsing a PMC JATS XML article
- **THEN** the adapter SHALL extract title, abstract, IMRaD sections, tables (with captions), figures (captions + URIs), and references

### Requirement: ClinicalTrials.gov v2 Adapter

The system SHALL ingest clinical trial data from ClinicalTrials.gov API v2 (JSON) with support for search queries and full protocol retrieval.

#### Scenario: Search by condition

- **WHEN** searching with query.cond="heart attack" and pageSize=100
- **THEN** the adapter SHALL return studies and provide pageToken for continuation

#### Scenario: Full protocol extraction

- **WHEN** fetching study NCT01234567
- **THEN** the adapter SHALL extract NCT ID, title, status, phase, conditions, interventions, arms, eligibility (inclusion/exclusion), outcome measures, results (if available), and adverse events

#### Scenario: Version tracking

- **WHEN** a study is re-ingested
- **THEN** the adapter SHALL store the record_version and generate a new doc_id if content hash differs

### Requirement: openFDA Adapter

The system SHALL ingest adverse events, device incidents, labels, and NDC data from openFDA with API key support and Elasticsearch-style queries.

#### Scenario: FAERS drug events query

- **WHEN** querying /drug/event.json with search='reactionmeddrapt:"headache"' and limit=100
- **THEN** the adapter SHALL return adverse event records with harmonized openfda fields

#### Scenario: Rate limit with API key

- **WHEN** OPENFDA_API_KEY is provided
- **THEN** the adapter SHALL allow 240 requests per minute up to 120,000 per day

#### Scenario: MAUDE device events

- **WHEN** querying /device/event.json
- **THEN** the adapter SHALL return device adverse events with UDI-DI and event descriptions

### Requirement: DailyMed SPL Adapter

The system SHALL ingest structured product labels (SPL XML) from DailyMed with LOINC-coded section mapping.

#### Scenario: Fetch by setid

- **WHEN** fetching SPL by setid (GUID)
- **THEN** the adapter SHALL retrieve XML, parse LOINC sections (Indications, Dosage, Warnings, Adverse Reactions), extract NDC, RxCUI, UNII, and ingredient strengths

#### Scenario: LOINC section tagging

- **WHEN** parsing SPL section with code="34067-9"
- **THEN** the adapter SHALL tag all blocks from that section with meta.loinc_section="34067-9" and section_label="Indications and Usage"

### Requirement: RxNorm / RxNav Adapter

The system SHALL normalize drug names to RxCUI and resolve NDC properties via RxNav REST API.

#### Scenario: Drug name to RxCUI

- **WHEN** querying /rxcui?name="enalapril"
- **THEN** the adapter SHALL return matching RxCUI codes with term types (IN, SCD, BN)

#### Scenario: NDC properties lookup

- **WHEN** querying /ndcproperties?ndc="12345-678-90"
- **THEN** the adapter SHALL return RxCUI, proprietary name, and NDC status

### Requirement: MeSH RDF Adapter

The system SHALL retrieve MeSH descriptors via lookup API and execute SPARQL queries for topic tagging.

#### Scenario: Descriptor lookup

- **WHEN** querying /mesh/lookup/descriptor?label="Diabetes Mellitus"&match=contains
- **THEN** the adapter SHALL return MeSH descriptor IDs with preferred terms and tree numbers

#### Scenario: SPARQL query

- **WHEN** executing a SPARQL query against /mesh/sparql
- **THEN** the adapter SHALL return JSON results with bindings

### Requirement: UMLS Adapter

The system SHALL retrieve UMLS concepts and crosswalks via UTS API with API key authentication.

#### Scenario: CUI lookup

- **WHEN** querying CUI C0009044 with UMLS_API_KEY
- **THEN** the adapter SHALL return concept details including preferred name, definitions, source vocabularies, and semantic types

#### Scenario: Source vocabulary crosswalk

- **WHEN** querying a CUI
- **THEN** the adapter SHALL return codes from SNOMED CT, ICD-10, ICD-11, LOINC, RxNorm as available

### Requirement: LOINC FHIR Adapter

The system SHALL access LOINC codes via FHIR terminology server with basic authentication.

#### Scenario: CodeSystem lookup

- **WHEN** calling CodeSystem/$lookup with code="48642-3" and system="<http://loinc.org>"
- **THEN** the adapter SHALL return display name, definition, and properties (component, property, time, system, scale, method)

#### Scenario: ValueSet expansion

- **WHEN** calling ValueSet/$expand for a lab panel
- **THEN** the adapter SHALL return all member LOINC codes

### Requirement: ICD-11 API Adapter

The system SHALL retrieve ICD-11 codes via WHO API with OAuth2 client credentials authentication.

#### Scenario: OAuth2 token acquisition

- **WHEN** authenticating with WHO_ICD11_CLIENT_ID and WHO_ICD11_CLIENT_SECRET
- **THEN** the adapter SHALL obtain an access token with scope=icdapi_access

#### Scenario: Entity retrieval

- **WHEN** querying /icd/release/11/mms/{code}
- **THEN** the adapter SHALL return entity details with title, definition, parent, and inclusions/exclusions

### Requirement: SNOMED CT Snowstorm Adapter

The system SHALL access SNOMED CT concepts via Snowstorm FHIR server (read-only public endpoint).

#### Scenario: Concept lookup

- **WHEN** calling CodeSystem/$lookup with code="73211009" (diabetes mellitus) and system="<http://snomed.info/sct>"
- **THEN** the adapter SHALL return display name, FSN, and properties

#### Scenario: License respect

- **WHEN** accessing SNOMED CT data
- **THEN** the adapter SHALL enforce license gates per policy.yaml (require affiliate license for restricted territories)

### Requirement: NICE Syndication Adapter

The system SHALL ingest UK clinical guidelines from NICE Syndication API with API key and license compliance.

#### Scenario: Guidelines retrieval

- **WHEN** fetching guidance with NICE_API_KEY and Accept: application/vnd.nice.syndication.services+json
- **THEN** the adapter SHALL return structured guidelines with recommendation units

#### Scenario: Caching compliance

- **WHEN** NICE guidance is retrieved
- **THEN** the adapter SHALL respect caching cadence (daily/weekly refresh) per NICE licensing terms

### Requirement: CDC Socrata Adapter

The system SHALL query CDC open data via Socrata SODA API with optional App Token.

#### Scenario: Dataset query

- **WHEN** querying <https://data.cdc.gov/resource/{dataset}.json> with $select, $where, $limit, $offset
- **THEN** the adapter SHALL return JSON records with pagination support

#### Scenario: App Token usage

- **WHEN** X-App-Token header is provided
- **THEN** the adapter SHALL be subject to higher rate limits and better reliability

### Requirement: WHO GHO Adapter

The system SHALL retrieve global health indicators from WHO Global Health Observatory via OData API.

#### Scenario: Indicator query

- **WHEN** querying <https://ghoapi.azureedge.net/api/{indicator}>
- **THEN** the adapter SHALL return indicator data with country, year, and value dimensions

### Requirement: OpenPrescribing Adapter

The system SHALL retrieve NHS England prescribing data from OpenPrescribing API.

#### Scenario: Spending query

- **WHEN** querying /api/1.0/spending with BNF code and org filter
- **THEN** the adapter SHALL return prescribing volumes and costs per practice

#### Scenario: BNF code lookup

- **WHEN** searching BNF codes
- **THEN** the adapter SHALL return matching codes with names and categories

### Requirement: Device Registry Adapters

The system SHALL ingest device metadata from AccessGUDID and openFDA UDI endpoints.

#### Scenario: UDI-DI lookup

- **WHEN** querying by UDI-DI (e.g., GTIN-14)
- **THEN** the adapter SHALL return device attributes: brand, model, labeler, sterilization, MRI safety, implantable, life-support, size

#### Scenario: UDI validation

- **WHEN** a UDI-DI is provided
- **THEN** the adapter SHALL validate format (GTIN-14 with mod-10 check digit) and reject invalid IDs

### Requirement: Content Hashing and Idempotency

The system SHALL generate deterministic doc_id values using content hashing to enable idempotent ingestion.

#### Scenario: Doc ID generation

- **WHEN** ingesting a document
- **THEN** the system SHALL compute doc_id as `{source}:{id}#{version_or_date}:{hash12}` where hash12 is first 12 chars of SHA256(canonical_bytes)

#### Scenario: Idempotent re-ingestion

- **WHEN** the same document (same content hash) is ingested twice
- **THEN** the system SHALL skip processing and return existing doc_id

#### Scenario: Version change detection

- **WHEN** a document with the same ID but different content is ingested
- **THEN** the system SHALL generate a new doc_id with updated hash and version

### Requirement: Normalization Utilities

The system SHALL normalize all ingested text to UTF-8, Unicode NFC, collapsed whitespace, and detect language.

#### Scenario: Text normalization

- **WHEN** raw text contains non-UTF-8 encoding or NFKD Unicode
- **THEN** the normalizer SHALL convert to UTF-8 and NFC, collapse whitespace, and preserve raw_text

#### Scenario: De-hyphenation

- **WHEN** text contains end-of-line hyphens (e.g., "treat-\nment")
- **THEN** the normalizer SHALL join words only if dictionary confirms validity

#### Scenario: Language detection

- **WHEN** ingesting a document
- **THEN** the system SHALL detect language (ISO 639-1 code) using fasttext or CLD and set Document.language

### Requirement: Validation Layer

The system SHALL validate ingested documents against source-specific semantic rules before persisting.

#### Scenario: Required fields check

- **WHEN** validating a ClinicalTrials.gov study
- **THEN** the validator SHALL ensure NCT ID, title, and status are present

#### Scenario: ID format validation

- **WHEN** validating identifiers (NCT, PMID, RxCUI, UDI-DI)
- **THEN** the validator SHALL check format (regex) and checksums (where applicable)

#### Scenario: Numeric sanity checks

- **WHEN** validating study enrollment numbers
- **THEN** the validator SHALL reject negative values or implausibly large numbers (>10^6)

### Requirement: CLI Commands

The system SHALL provide command-line interface for triggering ingestion with auto-pipeline or PDF-only modes.

#### Scenario: Auto-pipeline ingestion

- **WHEN** running `med ingest ctgov --nct NCT01234567 --auto`
- **THEN** the system SHALL fetch, parse, validate, write IR, and trigger downstream processing (chunk → embed → index)

#### Scenario: PDF-only ingestion

- **WHEN** running `med ingest pdf --uri https://example.com/paper.pdf --doc-key DOC123`
- **THEN** the system SHALL download PDF, persist to object store, set ledger state=pdf_downloaded, and STOP (no auto processing)

#### Scenario: Batch ingestion

- **WHEN** running `med ingest pmc --batch input.ndjson --auto`
- **THEN** the system SHALL process each line (PMCID list) and ingest all documents

### Requirement: Monitoring and Metrics

The system SHALL emit metrics for ingestion throughput, success/failure rates, and rate limit consumption per source.

#### Scenario: Success rate tracking

- **WHEN** ingesting documents
- **THEN** the system SHALL emit metrics: ingest_total{source, status=success|failure}

#### Scenario: Throughput measurement

- **WHEN** batch ingesting
- **THEN** the system SHALL emit metrics: ingest_duration_seconds{source}, ingest_docs_per_sec{source}

#### Scenario: Rate limit monitoring

- **WHEN** approaching source rate limits
- **THEN** the system SHALL emit warnings and metrics: rate_limit_remaining{source, limit_type}

### Requirement: Licensing Enforcement

The system SHALL enforce licensing requirements per source and block operations that violate license terms.

#### Scenario: UMLS license gate

- **WHEN** UMLS adapter is invoked and LIC_UMLS is not configured
- **THEN** the system SHALL fail with clear error: "UMLS requires UTS license acceptance"

#### Scenario: SNOMED territory restriction

- **WHEN** SNOMED adapter is invoked and LIC_SNOMED does not include current territory
- **THEN** the system SHALL either block access or redact SNOMED labels (per policy.yaml)

#### Scenario: MedDRA subscription check

- **WHEN** MedDRA mapping is requested and LIC_MEDDRA=false
- **THEN** the system SHALL skip MedDRA PT codes and log redaction event
