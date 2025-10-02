# Implementation Tasks

## 1. Foundation

- [ ] 1.1 Create HTTP client with retries, rate limiting, per-host throttling (`connectors/http_client.py`)
- [ ] 1.2 Implement ledger system (states: pdf_downloaded, auto_inflight, auto_done, *_failed) with JSONL persistence
- [ ] 1.3 Create base Adapter interface (`fetch`, `parse`, `validate`, `write`)
- [ ] 1.4 Implement content hashing (SHA256) and doc_id generation (`{source}:{id}#{version}:{hash12}`)
- [ ] 1.5 Create normalization utilities (UTF-8, NFKC, whitespace, de-hyphenation, language detection)
- [ ] 1.6 Add test fixtures for each source (sample responses)

## 2. Literature & Preprints

- [ ] 2.1 Implement PubMed E-utilities adapter (ESearch, EFetch, ESummary with usehistory paging)
- [ ] 2.2 Implement PMC OAI-PMH adapter (ListRecords with resumptionToken)
- [ ] 2.3 Implement medRxiv adapter (details endpoint with cursor paging)
- [ ] 2.4 Add rate limit handling (3 rps → 10 rps with API key for NCBI)

## 3. Clinical Trials

- [ ] 3.1 Implement ClinicalTrials.gov v2 adapter (search_studies, get_study with pageToken)
- [ ] 3.2 Parse protocol sections (eligibility, outcome measures, arms, results, AEs)
- [ ] 3.3 Store record_version for change tracking
- [ ] 3.4 Add validation for NCT ID format

## 4. Drug & Device Safety

- [ ] 4.1 Implement openFDA adapter (FAERS /drug/event, MAUDE /device/event, Labels, NDC)
- [ ] 4.2 Handle Elasticsearch-style search params and pagination
- [ ] 4.3 Add API key support (240 rpm with key vs 1k/day without)
- [ ] 4.4 Implement DailyMed SPL adapter (by setid/NDC; parse LOINC-coded sections)
- [ ] 4.5 Implement RxNav/RxNorm adapter (rxcui, ndcproperties endpoints)

## 5. Clinical Terminologies

- [ ] 5.1 Implement MeSH RDF adapter (lookup/descriptor endpoint + SPARQL queries)
- [ ] 5.2 Implement UMLS adapter (UTS API key authentication; CUI lookups)
- [ ] 5.3 Implement LOINC FHIR adapter (CodeSystem/$lookup, ValueSet/$expand with basic auth)
- [ ] 5.4 Implement ICD-11 API adapter (OAuth2 client credentials flow; /mms/{code} endpoint)
- [ ] 5.5 Implement SNOMED CT Snowstorm adapter (FHIR CodeSystem/$lookup, ValueSet/$expand)

## 6. Guidelines & Practice Data

- [ ] 6.1 Implement NICE Syndication adapter (API key + license compliance; JSON format)
- [ ] 6.2 Implement USPSTF API stub (approval flow + auth once granted)
- [ ] 6.3 Implement CDC Socrata adapter (SODA API with $select/$where/$limit/$offset)
- [ ] 6.4 Implement CDC WONDER adapter (XML query system)
- [ ] 6.5 Implement WHO GHO adapter (OData queries for indicators)
- [ ] 6.6 Implement OpenPrescribing adapter (/api/1.0 endpoints for spending, org lookups)

## 7. Device Registries

- [ ] 7.1 Implement AccessGUDID adapter (query by UDI-DI; extract attributes)
- [ ] 7.2 Implement openFDA UDI adapter (device/udi endpoint)
- [ ] 7.3 Add UDI-DI validation (GTIN-14 with mod-10 check)

## 8. CLI & Integration

- [ ] 8.1 Create CLI commands (`med ingest {source} --{params} --auto`)
- [ ] 8.2 Implement auto-pipeline trigger (non-PDF sources)
- [ ] 8.3 Implement PDF-only download (stop at ledger state pdf_downloaded)
- [ ] 8.4 Add batch ingest support (NDJSON input with doc IDs)
- [ ] 8.5 Create monitoring metrics (per-source success/failure rates, throughput)

## 9. Validation & Testing

- [ ] 9.1 Implement per-source semantic validators (required fields, ID formats, value ranges)
- [ ] 9.2 Add unit tests for each adapter (mock responses)
- [ ] 9.3 Add integration tests (hit real APIs with fixtures; rate-limited)
- [ ] 9.4 Test idempotency (same doc ingested twice → same hash, skip)
- [ ] 9.5 Test failure modes (network errors, rate limits, auth failures)

## 10. Documentation & Runbooks

- [ ] 10.1 Document API key acquisition for each source
- [ ] 10.2 Create .env.example with all required keys
- [ ] 10.3 Write runbooks for common failures (rate limit exceeded, auth expired, source API changes)
- [ ] 10.4 Document licensing requirements per source (UMLS acceptance, SNOMED affiliate, MedDRA subscription)
