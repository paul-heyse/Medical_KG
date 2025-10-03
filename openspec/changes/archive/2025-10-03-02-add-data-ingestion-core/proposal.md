# Add Data Ingestion Core

## Why

The system requires reliable, production-grade ingestion of medical data from 12+ authoritative sources (PubMed, PMC, ClinicalTrials.gov, DailyMed, openFDA, device registries, guidelines, and clinical terminologies). These adapters are the foundation of the knowledge graph and must handle rate limits, auth, versioning, failures, and idempotency correctly.

## What Changes

- Create adapter framework with common HTTP client (retries, rate limiting, auth)
- Implement adapters for all medical data sources:
  - **PubMed E-utilities** (NCBI; API key; 10 rps)
  - **PMC OAI-PMH** (full-text OA articles; JATS XML)
  - **medRxiv** (preprints)
  - **ClinicalTrials.gov v2** (JSON; modernized API)
  - **openFDA** (FAERS drug events, MAUDE device events, NDC, Labels)
  - **DailyMed SPL** (structured product labels with LOINC sections)
  - **RxNorm / RxNav** (drug normalization)
  - **MeSH RDF** (topic tagging; SPARQL endpoint)
  - **UMLS** (crosswalks; requires UTS API key)
  - **LOINC FHIR** (lab codes; basic auth)
  - **ICD-11 API** (OAuth2 client credentials)
  - **SNOMED CT Snowstorm FHIR** (read-only public)
  - **NICE Syndication API** (UK guidelines; requires API key & license)
  - **USPSTF Prevention TaskForce API** (requires approval)
  - **CDC APIs** (Socrata SODA, WONDER, Content Services)
  - **WHO GHO OData** (global health indicators)
  - **OpenPrescribing** (NHS England prescribing data)
  - **AccessGUDID / openFDA UDI** (device registries)
- Implement ledger system for tracking ingestion status (pdf_downloaded, auto_done, failures)
- Create validation layer (schema + semantic checks per source)
- Implement idempotent writes to object store
- Add source-specific normalizers (UTF-8, NFKC, de-hyphenation, language detection)
- Create CLI commands: `med ingest {source} --{id} --auto`

## Impact

- **Affected specs**: NEW `data-ingestion` capability
- **Affected code**: NEW `/adapters/*`, `/connectors/*`, `src/Medical_KG/ingest/`
- **Dependencies**: Requires `.env` with API keys (NCBI, openFDA, UMLS, LOINC, ICD-11, NICE)
- **Infrastructure**: HTTP client with rate limiting; object store for raw artifacts
- **Licensing**: Must respect UMLS/SNOMED/MedDRA/NICE licensing terms per `policy.yaml`
