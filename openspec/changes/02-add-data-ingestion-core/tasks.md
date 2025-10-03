# Implementation Tasks

## 1. Foundation

- [x] 1.1 Create HTTP client with retries, rate limiting, per-host throttling (`connectors/http_client.py`)
- [x] 1.2 Implement ledger system (states: pdf_downloaded, auto_inflight, auto_done, *_failed) with JSONL persistence
- [x] 1.3 Create base Adapter interface (`fetch`, `parse`, `validate`, `write`)
- [x] 1.4 Implement content hashing (SHA256) and doc_id generation (`{source}:{id}#{version}:{hash12}`)
- [x] 1.5 Create normalization utilities (UTF-8, NFKC, whitespace, de-hyphenation, language detection)
- [x] 1.6 Add test fixtures for each source (sample responses)

## 2. Literature & Preprints

- [x] 2.1 Implement PubMed E-utilities adapter (ESearch, EFetch, ESummary with usehistory paging)
- [x] 2.2 Implement PMC OAI-PMH adapter (ListRecords with resumptionToken)
- [x] 2.3 Implement medRxiv adapter (details endpoint with cursor paging)
- [x] 2.4 Add rate limit handling (3 rps → 10 rps with API key for NCBI)

## 3. Clinical Trials

- [x] 3.1 Implement ClinicalTrials.gov v2 adapter (search_studies, get_study with pageToken)
- [x] 3.2 Parse protocol sections (eligibility, outcome measures, arms, results, AEs)
- [x] 3.3 Store record_version for change tracking
- [x] 3.4 Add validation for NCT ID format

## 4. Drug & Device Safety

- [x] 4.1 Implement openFDA adapter (FAERS /drug/event, MAUDE /device/event, Labels, NDC)
- [x] 4.2 Handle Elasticsearch-style search params and pagination
- [x] 4.3 Add API key support (240 rpm with key vs 1k/day without)
- [x] 4.4 Implement DailyMed SPL adapter (by setid/NDC; parse LOINC-coded sections)
- [x] 4.5 Implement RxNav/RxNorm adapter (rxcui, ndcproperties endpoints)

## 5. Clinical Terminologies

- [x] 5.1 Implement MeSH RDF adapter (lookup/descriptor endpoint + SPARQL queries)
- [x] 5.2 Implement UMLS adapter (UTS API key authentication; CUI lookups)
- [x] 5.3 Implement LOINC FHIR adapter (CodeSystem/$lookup, ValueSet/$expand with basic auth)
- [x] 5.4 Implement ICD-11 API adapter (OAuth2 client credentials flow; /mms/{code} endpoint)
- [x] 5.5 Implement SNOMED CT Snowstorm adapter (FHIR CodeSystem/$lookup, ValueSet/$expand)

## 6. Guidelines & Practice Data

- [x] 6.1 Implement NICE Syndication adapter (API key + license compliance; JSON format)
- [x] 6.2 Implement USPSTF API stub (approval flow + auth once granted)
- [x] 6.3 Implement CDC Socrata adapter (SODA API with $select/$where/$limit/$offset)
- [x] 6.4 Implement CDC WONDER adapter (XML query system)
- [x] 6.5 Implement WHO GHO adapter (OData queries for indicators)
- [x] 6.6 Implement OpenPrescribing adapter (/api/1.0 endpoints for spending, org lookups)

## 7. Device Registries

- [x] 7.1 Implement AccessGUDID adapter (query by UDI-DI; extract attributes)
- [x] 7.2 Implement openFDA UDI adapter (device/udi endpoint)
- [x] 7.3 Add UDI-DI validation (GTIN-14 with mod-10 check)

## 8. CLI & Integration

- [x] 8.1 Create CLI commands (`med ingest {source} --{params} --auto`)
- [x] 8.2 Implement auto-pipeline trigger (non-PDF sources)
- [x] 8.3 Implement PDF-only download (stop at ledger state pdf_downloaded)
- [x] 8.4 Add batch ingest support (NDJSON input with doc IDs)
- [x] 8.5 Create monitoring metrics (per-source success/failure rates, throughput)

## 9. Validation & Testing

- [x] 9.1 Implement per-source semantic validators (required fields, ID formats, value ranges)
- [x] 9.2 Add unit tests for each adapter (mock responses)
- [x] 9.3 Add integration tests (hit real APIs with fixtures; rate-limited)
- [x] 9.4 Test idempotency (same doc ingested twice → same hash, skip)
- [x] 9.5 Test failure modes (network errors, rate limits, auth failures)

## 10. Documentation & Runbooks

- [x] 10.1 Document API key acquisition for each source
- [x] 10.2 Create .env.example with all required keys
- [x] 10.3 Write runbooks for common failures (rate limit exceeded, auth expired, source API changes)
- [x] 10.4 Document licensing requirements per source (UMLS acceptance, SNOMED affiliate, MedDRA subscription)
