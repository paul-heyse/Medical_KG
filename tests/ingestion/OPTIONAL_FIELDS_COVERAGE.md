# Optional Field Coverage Matrix

The table below captures which optional fields are commonly observed in the bootstrap fixtures
versus those that are rarely populated in source payloads. "Present" scenarios map to fixture
functions ending with `_with_optional_fields` while "Absent" scenarios remove the same keys to
exercise adapter resilience.

| Adapter | Optional Fields | Commonly Present | Rarely Present | Fixture Pair |
|---------|-----------------|------------------|----------------|--------------|
| ClinicalTrials.gov | `status`, `phase`, `study_type`, `lead_sponsor`, `enrollment`, `start_date`, `completion_date`, `outcomes` | `status`, `lead_sponsor`, `start_date` | `completion_date`, `outcomes` | `clinical_study_with_optional_fields` / `clinical_study_without_optional_fields` |
| AccessGUDID | `brand`, `model`, `company`, `description` | `brand`, `description` | `model`, `company` | `accessgudid_record` / `accessgudid_record_without_optional_fields` |
| RxNorm | `name`, `synonym`, `tty`, `ndc` | `name`, `tty` | `synonym`, `ndc` | `rxnav_properties` / `rxnav_properties_without_optional_fields` |
| PubMed | `pmcid`, `doi`, `journal`, `pub_year`, `pubdate` | `doi`, `journal`, `pub_year` | `pmcid`, `pubdate` | `pubmed_document_with_optional_fields` / `pubmed_document_without_optional_fields` |
| MedRxiv | `date` | `date` | — | `medrxiv_record` / `medrxiv_record_without_date` |
| NICE Guidelines | `url`, `licence` | `url` | `licence` | `nice_guideline_with_optional_fields` / `nice_guideline_without_optional_fields` |
| USPSTF | `id`, `status`, `url` | `status`, `url` | `id` | `uspstf_record_with_optional_fields` / `uspstf_record_without_optional_fields` |
| WHO GHO | `indicator`, `country`, `year` | `indicator`, `country` | `year` | `who_gho_record_with_optional_fields` / `who_gho_record_without_optional_fields` |

Adapters without `NotRequired` fields (e.g., CDC Socrata, CDC WONDER, OpenPrescribing) still rely on
paired fixtures so validation pathways observe empty payloads, but they are omitted from the table
for clarity.
