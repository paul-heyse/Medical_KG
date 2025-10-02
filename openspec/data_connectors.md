## Coverage map (medical only)

| Domain slice                  | Primary sources (APIs, feeds, datasets)                                                       | Why it matters for *real* clinical work                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Evidence & preprints          | **PubMed E‑utilities**, **PMC OAI‑PMH**, **medRxiv**                                          | High‑velocity evidence & free full‑text (PMC) for pathways, order sets, policy memos. ([NLM Support Center][1])           |
| Clinical trials               | **ClinicalTrials.gov API v2**                                                                 | Protocols, eligibility, outcomes; real trial status/locations for referral workflows. ([National Library of Medicine][2]) |
| Drug & device safety, labels  | **openFDA** (FAERS, MAUDE, Labels, NDC), **DailyMed** (SPL), **RxNav/RxNorm**                 | Pharmacovigilance signals & device incidents, ground‑truth labeling, NDC↔RxCUI normalization.                             |
| Terminologies                 | **MeSH RDF/SPARQL**, **UMLS**, **LOINC FHIR**, **ICD‑11 API**, **SNOMED CT (Snowstorm FHIR)** | Robust coding/crosswalks to normalize intake data and author computable guidelines. ([MeSH Linked Data][3])               |
| Guidelines & pathways         | **NICE Syndication API**, **USPSTF Prevention TaskForce API**                                 | Machine‑consumable guidance for order sets and CDS nudges; clinician‑facing recommendations. ([NICE][4])                  |
| Public health & practice      | **CDC APIs (Socrata SODA, WONDER, Content Services)**, **WHO GHO OData**                      | Surveillance, population denominators, and messaging content for pragmatic decisions. ([Socrata Developers][5])           |
| Real‑world EHR (credentialed) | **MIMIC‑IV, eICU‑CRD (PhysioNet)**                                                            | Real clinician actions (orders, labs, notes) to train/test realistic agents; requires DUA/CITI. ([PhysioNet][6])          |
| Prescribing in the wild       | **OpenPrescribing (NHS England)**                                                             | Operational, practitioner‑level prescribing & spend to anchor “what clinicians actually do.” ([openprescribing.net][7])   |

> 📦 The repo contains working Python connectors for every public API above (plus stubs with auth flow for credentialed sources): `connectors/*.py`, examples in `examples/`. See README inside the zip.

---

## Repo‑ready connection notes (medical)

Below I’ve documented, **for each source**, how to access it, credentials/signup, rate limits, response shapes, typical queries, and practical considerations for agents. Where applicable I include stability & licensing notes.

> 🔧 **Code:** All endpoints below are implemented in the repo. File paths are shown like `connectors/openfda.py`.

### 1) Literature & Preprints

#### 1.1 PubMed — NCBI E‑utilities

* **Base:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` (ESearch/Efetch/ESummary) ([NCBI][8])
* **Auth & limits:** 3 req/s without key; ~10 req/s with `api_key` query param. Use `usehistory=y` to page via `WebEnv` + `query_key`. Max 10,000 UIDs per single ESearch. ([NLM Support Center][1])
* **Formats:** JSON (via `retmode=json`) for ESearch/ESummary; XML/Medline for EFetch. ([NCBI][8])
* **Connector:** `connectors/pubmed_eutils.py` → `iter_history(query, batch_size=1000, mindate=..., maxdate=..., api_key=...)`.
* **Agent tips:** Always throttle, set `retmax=0` first to get counts; prefer `ESummary` for metadata and fetch full text links via PMC IDs as needed.

#### 1.2 PubMed Central (PMC) — OAI‑PMH (full text)

* **Base:** `https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/` (OAI verbs; we use `ListRecords`). ([PMC][9])
* **Params:** `verb=ListRecords`, `metadataPrefix=pmc` (or `oai_dc`), `set=pmc`, `from=YYYY-MM-DD`, `until=YYYY-MM-DD`. Use `resumptionToken` until exhausted.
* **Connector:** `connectors/pmc_oaipmh.py` (yields raw XML for downstream JATS parsing).
* **Agent tips:** Harvest in date slices; parse JATS; capture license tags to filter for re‑use.

#### 1.3 medRxiv (and bioRxiv)

* **Base:** `https://api.medrxiv.org` (`/details/{server}/{interval}/{cursor}/{format}`); servers: `medrxiv`, `biorxiv`. ([MedRxiv API][10])
* **Connector:** `connectors/medrxiv.py` → `details("medrxiv", "2025-09-01/2025-09-30", cursor=0)`.
* **Agent tips:** medRxiv is noisy—down‑weight or require confirmatory sources before producing operational recommendations.

---

### 2) Clinical Trials

#### ClinicalTrials.gov — **API v2 (modernized)**

* **Base:** `https://clinicaltrials.gov/api/v2/` (JSON, OpenAPI 3). ([National Library of Medicine][2])
* **Search endpoint:** `/studies` with query params like `query.cond`, `query.term`, `pageSize`, `pageToken`, `countTotal=true`. Example: `query.cond=heart attack`. ([BioMCP][11])
* **Detail endpoint:** `/studies/{NCT_ID}` (returns full protocol sections).
* **Connector:** `connectors/clinicaltrials_gov_v2.py` (`search_studies`, `get_study`).
* **Agent tips:** Respect pagination tokens; store `protocolSection.identificationModule.nctId` as stable key; prefer v2 enums for `interventionType` and ISO 8601 dates. (v2 migration guide explains differences from legacy.) ([ClinicalTrials.gov][12])

---

### 3) Drug & Device Safety, Labeling, Normalization

#### 3.1 **openFDA** (FAERS drug events, MAUDE device events, Labels, NDC)

* **Base:** `https://api.fda.gov` (Elasticsearch‑style `search` & `count` params). ([OpenFDA][13])
* **Auth & limits:** API key recommended. openFDA lists: *no key* 240 rpm / 1,000 per day per IP; *key* 240 rpm / 120,000 per day. Pass as `api_key` or Basic auth username. HTTPS required.
* **Key endpoints:**

  * **FAERS:** `/drug/event.json` (fields include `reactionmeddrapt`, harmonized `openfda.*`). ([OpenFDA][14])
  * **MAUDE (devices):** `/device/event.json`. ([OpenFDA][15])
  * **Labels:** `/drug/label.json`; **NDC:** `/drug/ndc.json`. ([OpenFDA][16])
  * **Bulk downloads:** zipped JSON by endpoint (drug/ device events, labels, etc.). ([OpenFDA][17])
* **Connector:** `connectors/openfda.py` → `query("/drug/event.json", {"search": 'reactionmeddrapt:"headache"', "limit": 5})`.
* **Agent tips:** FAERS/MAUDE are **spontaneous reports**—use for signals, not incidence. MedDRA terms are embedded (e.g., `reactionmeddrapt`) and use British English spellings. Licensing of MedDRA is separate (terms are represented in records but dictionary redistribution requires a license). ([OpenFDA][18])

#### 3.2 **DailyMed** (SPL labeling)

* **Base:** `https://dailymed.nlm.nih.gov/dailymed/services/v2` (REST; JSON/XML). Resources include `/spls`, `/spls/{SETID}`, `/ndcs/{ndc}/spls`, `/drugclasses`, `/rxcuis`. ZIP/PDF download links provided. ([DailyMed][19])
* **Connector:** `connectors/dailymed.py`.
* **Agent tips:** Use DailyMed to ground label sections and link to RxCUI/UNII; track `X-DAILYMED-LABEL-LAST-UPDATED` headers for cache invalidation. ([DailyMed][19])

#### 3.3 **RxNav / RxNorm**

* **Base:** `https://rxnav.nlm.nih.gov/REST` (no auth required for common endpoints). ([Lister Hill Center][20])
* **Endpoints:** `/rxcui?name=...`, `/drugs?name=...`, `/ndcproperties?ndc=...`.
* **Connector:** `connectors/rxnorm.py`.
* **Agent tips:** Use RxNorm to normalize brand/generic, roll up by ingredient, and to bridge NDCs from claims/prescribing back to clinical language.

---

### 4) Clinical Terminologies & Crosswalks

#### 4.1 **MeSH RDF** (RDF/REST/SPARQL)

* **Lookup:** `https://id.nlm.nih.gov/mesh/lookup/descriptor?label=...&match=contains`
* **SPARQL:** `https://id.nlm.nih.gov/mesh/sparql` (JSON results). ([MeSH Linked Data][3])
* **Connector:** `connectors/mesh.py`.
* **Agent tips:** Perfect for tagging evidence, topic clustering, and query expansion.

#### 4.2 **UMLS** (UTS license; REST API)

* **Base:** `https://uts-ws.nlm.nih.gov/rest`
* **Auth:** **New** method: append `apiKey` to requests (no CAS tickets needed). Get a UTS account + API key. ([UMLS Terminology Services][21])
* **Connector:** `connectors/umls.py` (example: `get_cui("C0009044")`).
* **Agent tips:** Use CUIs as the “hub” for crosswalking SNOMED, ICD‑10/11, LOINC, RxNorm.

#### 4.3 **LOINC FHIR** (terminology server; auth required)

* **Base:** `https://fhir.loinc.org`
* **Auth:** LOINC account (username/password). Endpoints include `CodeSystem/$lookup` and `ValueSet/$expand`. ([LOINC][22])
* **Connector:** `connectors/loinc_fhir.py`.

#### 4.4 **ICD‑11 API** (WHO; OAuth2 client credentials)

* **Token:** `https://icdaccessmanagement.who.int/connect/token`; **Base:** `https://id.who.int/icd/release/11/` (e.g., `/mms/{code}`). Uses OAuth2 client credentials with scope `icdapi_access`. ([ICD 11][23])
* **Connector:** `connectors/icd11_api.py`.

#### 4.5 **SNOMED CT** (Snowstorm FHIR read‑only)

* **Base:** `https://snowstorm.ihtsdotools.org/fhir` (e.g., `CodeSystem/$lookup`, `ValueSet/$expand`). The server backs the official SNOMED browser. Respect SNOMED licensing terms. ([GitHub][24])
* **Connector:** `connectors/snomed_fhir.py`.

---

### 5) Clinical Guidelines & Practitioner Pathways

#### 5.1 **NICE Syndication API** (UK)

* **Guide:** Corporate doc ECD10 covers licensing, API key, formats (`application/vnd.nice.syndication.services+json`), and caching rules (daily/weekly refresh). UK use is fee‑free under the NICE UK open content licence; non‑UK commercial use has fees. Apply for a licence and API key. ([NICE][4])
* **Connector:** `connectors/nice_syndication.py` (requires `NICE_API_KEY`).

#### 5.2 **USPSTF Prevention TaskForce API** (US)

* **Access:** Requires prior approval (email request); returns JSON tailored by patient age/sex/risk. ([USPSTF][25])
* **Connector:** `connectors/uspstf_api.py` (stub + notes until approval).

> **Bonus, for care‑process anchoring**: widely used checklists & bundles you may want to cache (for semantic retrieval by agents):
>
> * **WHO Surgical Safety Checklist** (19 items; PDF and implementation manual). ([World Health Organization][26])
> * **Surviving Sepsis Campaign 2021** (adult guideline + Hour‑1 bundle). ([Society of Critical Care Medicine (SCCM)][27])

---

### 6) Public Health & Practice Data

#### 6.1 **CDC** (multiple)

* **Socrata SODA APIs** (`https://data.cdc.gov/resource/{dataset}.json`) with `$select/$where/$limit/$offset`, App Token optional in `X-App-Token`. ([Socrata Developers][5])
* **WONDER API** (XML over HTTP for specific query systems). ([CDC WONDER][28])
* **CDC Content Services** (for site content in JSON/XML; sometimes proxied via api.data.gov rate‑limits). ([CDC Tools][29])
* **Connector:** `connectors/cdc_socrata.py`.

#### 6.2 **WHO Global Health Observatory (OData)**

* **Base:** `https://ghoapi.azureedge.net/api` (OData). Good for denominators and indicators. ([World Health Organization][30])
* **Connector:** `connectors/who_gho.py`.

#### 6.3 **OpenPrescribing (NHS England)**

* **Base/API:** `https://openprescribing.net/api/1.0` (spending, org lookups, BNF code search; JSON/CSV). No registration as of today. ([openprescribing.net][7])
* **Connector:** `connectors/openprescribing.py`.

---

### 7) Credentialed EHR Research Datasets (for real‑world clinical behavior)

#### **MIMIC‑IV**, **eICU‑CRD** (PhysioNet)

* **Access:** Complete **CITI “Data or Specimens Only Research”** training and sign the **PhysioNet Credentialed Health Data Use Agreement (CHD‑DUA)**; access is granted to credentialed users only. ([PhysioNet][6])
* **Use:** Order sets, notes, lab/vitals, diagnostics—the data your agents need to mimic day‑to‑day clinical reasoning (de‑identified).
* **Implementation:** These are downloads (not APIs). Stage in an object store, convert to OMOP/FHIR if needed.

---

## Practical implementation details

### Authentication & secrets

* Use `.env` (template provided) for: `NCBI_EUTILS_API_KEY`, `OPENFDA_API_KEY`, `UMLS_API_KEY`, `LOINC_FHIR_USERNAME/PASSWORD`, `WHO_ICD11_CLIENT_ID/SECRET`, `NICE_API_KEY`.
* The repo’s HTTP client auto‑handles retries and basic rate limiting per host (`connectors/http_client.py`).
* **openFDA**: pass `api_key` as query param (or Basic auth username). HTTPS required.
* **UMLS**: new API key model; append `apiKey` to requests. ([UMLS Terminology Services][21])
* **ICD‑11**: obtain OAuth2 token first, then call ICD endpoints with `Authorization: Bearer`. ([ICD 11][23])
* **LOINC**: basic auth to `fhir.loinc.org`. ([LOINC][22])
* **NICE**: `Ocp-Apim-Subscription-Key` header; abide by caching rules. ([NICE][4])

### Rate limits (operational)

* **NCBI E‑utilities:** ~3 rps w/out key; ~10 rps with key. Back off on 429. ([NLM Support Center][1])
* **openFDA:** 240 rpm; 1k/day (no key) vs 120k/day (key).
* **Socrata (CDC open data):** many datasets accept unlimited without token but are *much* more reliable with an App Token. ([Socrata Developers][5])
* **ClinicalTrials.gov v2:** public, no keys; page with `pageToken` and `pageSize`. ([National Library of Medicine][2])

### Field normalization & standards

* **Drugs** → normalize to **RxNorm** (ingredient/form/brand). ([Lister Hill Center][20])
* **Lab tests** → LOINC lookup/expand for FHIR ValueSets. ([LOINC][22])
* **Diagnoses** → ICD‑11/SNOMED concepts; maintain UMLS CUI crosswalks for joins. ([ICD 11][23])
* **Topics** → tag with **MeSH** to anchor literature/guidelines retrieval. ([MeSH Linked Data][3])

### Example agent flows

* **Safety signal drill‑down:** openFDA FAERS (`reactionmeddrapt:"myocardial infarction"`) → DailyMed label sections (Warnings/Precautions) → PubMed/PMC for mechanistic evidence → emit clinician‑facing brief with RxNorm normalized drug names. ([OpenFDA][18])
* **Trial referral:** ClinicalTrials.gov v2 (`query.cond=glioblastoma`) → filter by `recruiting` and `locationCountry` → produce patient‑matching check using eligibility snippets. ([National Library of Medicine][2])
* **Order‑set validation:** Surviving Sepsis Hour‑1 bundle items cross‑checked against ICU EHR orders in MIMIC (where permitted) to ensure realistic steps. ([Society of Critical Care Medicine (SCCM)][31])

---

## Constraints, licensing, and “gotchas”

* **Spontaneous reporting bias** in FAERS/MAUDE (no denominators; not incidence). Treat as signal only. ([fis.fda.gov][32])
* **MedDRA** terms appear in FAERS but the **dictionary** is separately licensed; don’t redistribute MedDRA content. ([MedDRA][33])
* **NICE syndication**: licence & caching cadence (UK vs non‑UK fee model). ([NICE][4])
* **UMLS/LOINC/SNOMED**: respect licence terms; UMLS requires annual account; LOINC login for FHIR server; SNOMED rights vary by country. ([UMLS Terminology Services][21])
* **MIMIC/eICU**: require CITI training + CHD‑DUA; de‑identified; no attempt at re‑identification. ([PhysioNet][6])

---

## What’s in the zip (structure)

* `connectors/`

  * `http_client.py` — requests session w/ retries & per‑host rate limiting.
  * `pubmed_eutils.py`, `pmc_oaipmh.py`, `medrxiv.py`
  * `clinicaltrials_gov_v2.py`
  * `openfda.py`, `dailymed.py`, `rxnorm.py`
  * `mesh.py`, `umls.py`, `loinc_fhir.py`, `icd11_api.py`, `snomed_fhir.py`
  * `nice_syndication.py`, `uspstf_api.py` (stub), `cdc_socrata.py`, `who_gho.py`, `openprescribing.py`
* `examples/`

  * `pubmed_search.py`, `openfda_faers.py`, `ctgov_search.py`, `openprescribing.py`
* `docs/connection_notes_medical.md` — concise repo copy of the above
* `.env.example`, `requirements.txt`, `pyproject.toml`, `README.md`

> **Try it quickly**
>
> ```bash
> pip install -r requirements.txt
> python examples/openfda_faers.py
> python examples/ctgov_search.py
> python examples/pubmed_search.py "sepsis lactate resuscitation"
> ```

---

## Source‑by‑source “quick cards” (copy into agent specs)

**PubMed (E‑utilities)**
**Base:** `/entrez/eutils/` • **Auth:** optional key • **Limit:** 3 rps (10 rps with key) • **Best for:** literature ids & summaries • **Key params:** `term, retmode, usehistory=y, retstart/retmax` • **Pitfalls:** page >10k via WebEnv • **Docs:** ([NLM Support Center][1])

**PMC OAI‑PMH**
**Base:** `/api/oai/v1/mh/` • **Auth:** none • **Best for:** OA full text • **Key params:** `ListRecords, metadataPrefix, set, from, until` • **Docs:** ([PMC][9])

**medRxiv**
**Base:** `/details/{server}/{interval}/{cursor}/{format}` • **Auth:** none • **Best for:** latest preprints • **Docs:** ([MedRxiv API][10])

**ClinicalTrials.gov v2**
**Base:** `/api/v2/studies` • **Auth:** none • **Best for:** trial search (condition, interventions), live status • **Key params:** `query.cond`, `query.term`, `pageSize`, `pageToken` • **Docs:** ([National Library of Medicine][2])

**openFDA**
**Base:** `api.fda.gov` • **Auth:** `api_key` recommended • **Limit:** 240 rpm; daily quotas by key/IP • **Best for:** FAERS, MAUDE, labels • **Docs:**

**DailyMed**
**Base:** `/dailymed/services/v2` • **Auth:** none • **Best for:** SPL & labeling metadata, setid, NDC mapping • **Docs:** ([DailyMed][19])

**RxNav/RxNorm**
**Base:** `rxnav.nlm.nih.gov/REST` • **Auth:** none • **Best for:** drug normalization & NDC properties • **Docs:** ([Lister Hill Center][20])

**MeSH RDF**
**Base:** `id.nlm.nih.gov/mesh` • **Auth:** none • **Best for:** topic tagging & SPARQL • **Docs:** ([MeSH Linked Data][3])

**UMLS**
**Base:** `uts-ws.nlm.nih.gov/rest` • **Auth:** UTS API key (append `apiKey`) • **Best for:** CUIs & crosswalks • **Docs:** ([UMLS Terminology Services][21])

**LOINC FHIR**
**Base:** `fhir.loinc.org` • **Auth:** LOINC account • **Best for:** lab code lookup/expand • **Docs:** ([LOINC][22])

**ICD‑11 API**
**Base:** `id.who.int/icd/release/11/` • **Auth:** OAuth2 client credentials (WHO) • **Best for:** ICD‑11 concepts • **Docs:** ([ICD 11][23])

**SNOMED CT (Snowstorm FHIR)**
**Base:** `snowstorm.ihtsdotools.org/fhir` • **Auth:** public read (respect license) • **Best for:** concept lookup & ValueSet expand • **Docs:** ([GitHub][24])

**NICE Syndication**
**Base:** `api.nice.org.uk` • **Auth:** API key; licence types & caching • **Best for:** machine‑readable guidance • **Docs:** ([NICE][4])

**USPSTF Prevention TaskForce**
**Base:** (upon approval) • **Auth:** apply via email • **Best for:** primary‑care recommendations by age/sex/risk • **Docs:** ([USPSTF][25])

**CDC (Socrata/WONDER/Content Services)**
**Base:** `data.cdc.gov/resource/*.json`, WONDER XML, `tools.cdc.gov/api` • **Auth:** optional App Token / various • **Best for:** surveillance & content • **Docs:** ([Socrata Developers][5])

**WHO GHO**
**Base:** `ghoapi.azureedge.net/api` • **Auth:** none • **Best for:** international indicators • **Docs:** ([World Health Organization][30])

**OpenPrescribing**
**Base:** `openprescribing.net/api/1.0` • **Auth:** none • **Best for:** practice‑level prescribing & spend • **Docs:** ([openprescribing.net][7])

**MIMIC‑IV, eICU‑CRD (credentialed)**
**Access:** CITI + CHD‑DUA • **Best for:** real clinician orders/labs/notes • **Docs:** ([PhysioNet][6])

---

## How your agents should use this

1. **Normalize** everything (RxNorm/LOINC/ICD/SNOMED/MeSH) at ingest to enable precise retrieval and deduplication. ([Lister Hill Center][20])
2. **Blend** safety signals (openFDA) with labels (DailyMed) + evidence (PubMed/PMC) before giving operational advice. ([OpenFDA][14])
3. **Cache & respect quotas** (NICE caching cadence; openFDA quotas; NCBI RPS). ([NICE][4])
4. For **real‑world practice**: ground agents on OpenPrescribing (UK practice), CDC/WHO indicators (population context), and—where permitted—MIMIC/eICU patient‑level patterns. ([openprescribing.net][7])

---

### What you can run right now

* **FAERS top 5 “headache”**
  `python examples/openfda_faers.py` → calls `/drug/event.json?search=reactionmeddrapt:"headache"&limit=5` (daily quota managed by key). ([OpenFDA][18])
* **Trials for STEMI**
  `python examples/ctgov_search.py` → `query.cond=heart attack`, prints `nctId` + title. ([iqwig.de][34])
* **PubMed paging**
  `python examples/pubmed_search.py "sepsis lactate resuscitation"` uses ESearch `usehistory=y` to page safely. ([NCBI][8])

---

If you want me to extend this further (e.g., add **FHIR exports**, **OMOP mappings**, or **data governance checklists** per source), I can deliver that next.

[1]: https://support.nlm.nih.gov/kbArticle/?pn=KA-05318&utm_source=chatgpt.com "How do I get an enhanced API key (exceeding 10 rps) for ..."
[2]: https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html?utm_source=chatgpt.com "ClinicalTrials.gov API Version 2.0 Now Available"
[3]: https://id.nlm.nih.gov/mesh/lookup "MeSH RDF Lookup Service"
[4]: https://www.nice.org.uk/corporate/ecd10 "Introduction | NICE syndication service and application programming interface (API) guide  | Guidance | NICE"
[5]: https://dev.socrata.com/foundry/data.cdc.gov/xf9s-d895/embed?utm_source=chatgpt.com "dhds_dataset | Socrata API Foundry - Data & Insights"
[6]: https://physionet.org/content/mimiciv/?utm_source=chatgpt.com "MIMIC-IV v3.1"
[7]: https://openprescribing.net/api/ "API | OpenPrescribing"
[8]: https://www.ncbi.nlm.nih.gov/books/NBK25499/?utm_source=chatgpt.com "The E-utilities In-Depth: Parameters, Syntax and More"
[9]: https://pmc.ncbi.nlm.nih.gov/tools/oai/?utm_source=chatgpt.com "PMC OAI-PMH API"
[10]: https://api.medrxiv.org/?utm_source=chatgpt.com "bioRxiv API - medRxiv"
[11]: https://biomcp.org/backend-services-reference/04-clinicaltrials-gov/?utm_source=chatgpt.com "ClinicalTrials.gov API"
[12]: https://clinicaltrials.gov/data-api/about-api/api-migration?utm_source=chatgpt.com "API Migration Guide"
[13]: https://open.fda.gov/apis/?utm_source=chatgpt.com "About the openFDA API"
[14]: https://open.fda.gov/apis/drug/event/?utm_source=chatgpt.com "Drug Adverse Event Overview"
[15]: https://open.fda.gov/apis/device/event/?utm_source=chatgpt.com "Device Adverse Event Overview"
[16]: https://open.fda.gov/apis/drug/?utm_source=chatgpt.com "Drug API Endpoints"
[17]: https://open.fda.gov/apis/drug/event/download/?utm_source=chatgpt.com "Download the dataset"
[18]: https://open.fda.gov/apis/drug/event/how-to-use-the-endpoint/?utm_source=chatgpt.com "How to use the API"
[19]: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm "DailyMed - Web Services"
[20]: https://lhncbc.nlm.nih.gov/RxNav/?utm_source=chatgpt.com "RxNav - LHNCBC"
[21]: <https://documentation.uts.nlm.nih.gov/rest/authentication.html> "
      User Authentication

  "
[22]: <https://loinc.org/news/loincs-new-fhir-server-provides-programmatic-access-to-loinc-content/?utm_source=chatgpt.com> "LOINC's new FHIR server provides programmatic access to ..."
[23]: <https://icd.who.int/docs/icd-api/APIDoc-Version1/?utm_source=chatgpt.com> "ICD-API - ICD URIs and Supporting Web Services"
[24]: <https://github.com/IHTSDO/snowstorm?utm_source=chatgpt.com> "IHTSDO/snowstorm: Scalable SNOMED CT Terminology ..."
[25]: <https://www.uspreventiveservicestaskforce.org/apps/api.jsp> "U.S. Preventive Services | Prevention TaskForce API"
[26]: <https://www.who.int/docs/default-source/patient-safety/9789241598590-eng-checklist.pdf?utm_source=chatgpt.com> "Surgical Safety Checklist"
[27]: <https://www.sccm.org/clinical-resources/guidelines/guidelines/surviving-sepsis-guidelines-2021?utm_source=chatgpt.com> "Surviving Sepsis Campaign Guidelines 2021 | SCCM"
[28]: <https://wonder.cdc.gov/wonder/help/wonder-api.html?utm_source=chatgpt.com> "CDC WONDER API for Data Query Web Service"
[29]: <https://tools.cdc.gov/api/docs/info.aspx?utm_source=chatgpt.com> "CS API Reference"
[30]: <https://www.who.int/data/gho/info/gho-odata-api?utm_source=chatgpt.com> "GHO OData API"
[31]: <https://sccm.org/survivingsepsiscampaign/guidelines-and-resources/surviving-sepsis-campaign-adult-guidelines?utm_source=chatgpt.com> "Surviving Sepsis Campaign 2021 Adult Guidelines"
[32]: <https://fis.fda.gov/extensions/FPD-FAQ/FPD-FAQ.html?utm_source=chatgpt.com> "FAERS Public Dashboard - FAQ"
[33]: <https://www.meddra.org/node/2773?utm_source=chatgpt.com> "Terms & Conditions"
[34]: <https://www.iqwig.de/veranstaltungen/workshop-1-scells-apis.pdf?utm_source=chatgpt.com> "Using APIs to help automate information retrieval for ..."
