# Runtime Validation Audit

_Commit reference: 7468af41060dc001f7c505e08c48cd45512c8eb6_

This document enumerates every `ensure_json_*` runtime validation call in the
three targeted ingestion adapters prior to refactoring. Line numbers correspond
to the pre-change sources and will shift once redundant validation is removed.
Each entry identifies the surrounding context, classifies the call as boundary
validation (keep) or internal redundancy (remove), and records the rationale for
removal decisions.

## Clinical adapters (`src/Medical_KG/ingestion/adapters/clinical.py`)

34 call sites were identified across the clinical catalog adapters. Items 1–6
occur during the ClinicalTrials.gov fetch boundary; items 7–26 are the redundant
validation inside `ClinicalTrialsGovAdapter.parse`; items 27–34 cover the other
clinical adapters.

1. **L65 – ClinicalTrialsGovAdapter.fetch**: `payload_map = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Coerce ClinicalTrials.gov v2 API response into a mapping
   - **Decision**: Retained as the first point where external JSON enters the
     adapter; documents v2 schema expectations.
2. **L67 – ClinicalTrialsGovAdapter.fetch**: `for study_value in ensure_json_sequence(...)`
   - **Category**: Boundary (keep)
   - **Context**: Iterate over `studies` array from API response
   - **Decision**: Retained to guard against pagination schema changes.
3. **L68 – ClinicalTrialsGovAdapter.fetch**: `study_map = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Promote each study result into a mapping before building the
     typed payload stub
   - **Decision**: Retained to ensure each study has object structure.
4. **L69 – ClinicalTrialsGovAdapter.fetch**: `protocol_section = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Extract nested `protocolSection` block
   - **Decision**: Retained to guarantee the top-level typed payload contains a
     mapping for `protocolSection`.
5. **L79 – ClinicalTrialsGovAdapter.fetch**: `ensure_json_mapping(derived_section_value, ...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Guard already type-checked optional `derivedSection`
   - **Removal criteria**: `isinstance(..., Mapping)` already precedes the call;
     TypedDict payload stores a `dict`, so further coercion is unnecessary.
6. **L91 – ClinicalTrialsGovAdapter.parse**: `protocol = ensure_json_mapping(...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Promote `protocolSection` that the TypedDict already marks as a
     mapping
   - **Removal criteria**: `ClinicalTrialsStudyPayload.protocolSection` is typed
     as `JSONMapping`; rely on the type and default to `{}` when absent.
7. **L95 – ClinicalTrialsGovAdapter.parse**: `identification = ensure_json_mapping(...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Nested module extracted from `protocol`
   - **Removal criteria**: Gracefully handle non-mapping values with
     `isinstance` checks instead of runtime coercion.
8. **L102 – ClinicalTrialsGovAdapter.parse**: `status_module = ensure_json_mapping(...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Status module within protocol section
   - **Removal criteria**: Same as above; treat unexpected shapes as empty
     mappings.
9. **L109 – ClinicalTrialsGovAdapter.parse**: `description_module = ensure_json_mapping(...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Description module extraction
   - **Removal criteria**: Replace with defensive `Mapping` guard.
10. **L118 – ClinicalTrialsGovAdapter.parse**: `ensure_json_mapping(derived_section_value, ...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Optional `derivedSection` payload promoted into dict
    - **Removal criteria**: `Mapping` guard already ensures structure; convert
      using `dict()` only when appropriate.
11. **L122 – ClinicalTrialsGovAdapter.parse**: `misc_info = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Misc info module from derived section
    - **Removal criteria**: Replace with `Mapping` check.
12. **L128 – ClinicalTrialsGovAdapter.parse**: `sponsor_module = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Sponsor module extraction
    - **Removal criteria**: Use `Mapping` guard; default to `{}` when missing.
13. **L132 – ClinicalTrialsGovAdapter.parse**: `lead_sponsor_mapping = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Lead sponsor block inside sponsor module
    - **Removal criteria**: Handle gracefully with `Mapping` guard.
14. **L139 – ClinicalTrialsGovAdapter.parse**: `design_module = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Study design module
    - **Removal criteria**: Swap for `Mapping` guard.
15. **L146 – ClinicalTrialsGovAdapter.parse**: `for phase in ensure_json_sequence(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Iterate over `phases`
    - **Removal criteria**: Use `Sequence` guard that excludes str/bytes.
16. **L153 – ClinicalTrialsGovAdapter.parse**: `enrollment_info = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Enrollment metadata block
    - **Removal criteria**: Use `Mapping` guard.
17. **L166 – ClinicalTrialsGovAdapter.parse**: `start_date_struct = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Start date structure inside status module
    - **Removal criteria**: Use `Mapping` guard; default to empty dict.
18. **L173 – ClinicalTrialsGovAdapter.parse**: `completion_date_struct = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Completion date structure
    - **Removal criteria**: Same as above.
19. **L180 – ClinicalTrialsGovAdapter.parse**: `arms_module = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Arms/interventions module
    - **Removal criteria**: Use `Mapping` guard.
20. **L187 – ClinicalTrialsGovAdapter.parse**: `for arm in ensure_json_sequence(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Iterate over `arms`
    - **Removal criteria**: Sequence guard with str/bytes exclusion.
21. **L188 – ClinicalTrialsGovAdapter.parse**: `arms_list.append(ensure_json_mapping(...))`
    - **Category**: Internal redundancy (remove)
    - **Context**: Promote each arm entry to mapping
    - **Removal criteria**: Already confirmed `arm` is `Mapping`; use `dict()`.
22. **L190 – ClinicalTrialsGovAdapter.parse**: `eligibility_module = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Eligibility module extraction
    - **Removal criteria**: Replace with `Mapping` guard.
23. **L194 – ClinicalTrialsGovAdapter.parse**: `eligibility_value = ensure_json_value(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Coerce eligibility criteria text/value
    - **Removal criteria**: Use `_as_json_value` helper to normalise without
      recursive validation.
24. **L199 – ClinicalTrialsGovAdapter.parse**: `outcomes_module = ensure_json_mapping(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Outcomes module extraction
    - **Removal criteria**: Use `Mapping` guard.
25. **L206 – ClinicalTrialsGovAdapter.parse**: `for outcome in ensure_json_sequence(...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Iterate over primary outcomes list
    - **Removal criteria**: Sequence guard with str/bytes exclusion.
26. **L207 – ClinicalTrialsGovAdapter.parse**: `outcomes_list.append(ensure_json_mapping(...))`
    - **Category**: Internal redundancy (remove)
    - **Context**: Promote each outcome entry into mapping
    - **Removal criteria**: Already ensured entry is `Mapping`; convert with
      `dict()`.
27. **L299 – OpenFdaAdapter.fetch**: `payload_map = ensure_json_mapping(...)`
    - **Category**: Boundary (keep)
    - **Context**: Validate OpenFDA REST response envelope
    - **Decision**: Retained with API response comments.
28. **L301 – OpenFdaAdapter.fetch**: `for record_value in ensure_json_sequence(...)`
    - **Category**: Boundary (keep)
    - **Context**: Iterate over records array
    - **Decision**: Retained to guard future schema drift.
29. **L302 – OpenFdaAdapter.fetch**: `record_map = ensure_json_mapping(...)`
    - **Category**: Boundary (keep)
    - **Context**: Promote each record to mapping before yielding typed payload
    - **Decision**: Retained.
30. **L318 – OpenFdaAdapter.parse**: `ensure_json_value(value, context="openfda record field")`
    - **Category**: Internal redundancy (remove)
    - **Context**: Comprehension copying already-validated mapping values
    - **Removal criteria**: Replace with shallow dict copy; payload already
      satisfies `JSONMapping` contract.
31. **L426 – RxNormAdapter.fetch**: `yield ensure_json_mapping(payload, ...)`
    - **Category**: Boundary (keep)
    - **Context**: Validate RxNav properties response
    - **Decision**: Retained with comment referencing RxNav schema v1.
32. **L429 – RxNormAdapter.parse**: `props = ensure_json_mapping(raw.get("properties", {}), ...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Access nested `properties` mapping returned by fetch
    - **Removal criteria**: Replace with defensive `Mapping` guard.
33. **L499 – AccessGudidAdapter.fetch**: `yield ensure_json_mapping(payload, ...)`
    - **Category**: Boundary (keep)
    - **Context**: Validate AccessGUDID lookup response envelope
    - **Decision**: Retained.
34. **L502 – AccessGudidAdapter.parse**: `udi_mapping = ensure_json_mapping(raw.get("udi", {}), ...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Access nested `udi` mapping after fetch
    - **Removal criteria**: Use `Mapping` guard; default to `{}` when missing.

## Guidelines adapters (`src/Medical_KG/ingestion/adapters/guidelines.py`)

Twelve call sites were identified across the guideline/knowledge-base adapters.
Entries 1–9 occur in fetch boundaries; entry 10 is the sole redundant parse-time
validation; entries 11–12 are boundary validations for OpenPrescribing.

1. **L63 – NiceGuidelineAdapter.fetch**: `payload_map = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Ensure NICE API response root is an object
   - **Decision**: Retained; annotate with API schema version comment.
2. **L64 – NiceGuidelineAdapter.fetch**: `ensure_json_value(payload_value, ...)`
   - **Category**: Boundary (keep)
   - **Context**: Accept API response body as JSON value before mapping coercion
   - **Decision**: Retained; documents expectation that NICE returns JSON not XML.
3. **L68 – NiceGuidelineAdapter.fetch**: `items_sequence = ensure_json_sequence(...)`
   - **Category**: Boundary (keep)
   - **Context**: Iterate over guidance items array
   - **Decision**: Retained.
4. **L73 – NiceGuidelineAdapter.fetch**: `record_mapping = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Promote each guidance item into mapping before yield
   - **Decision**: Retained.
5. **L168 – CdcSocrataAdapter.fetch**: `rows = ensure_json_sequence(...)`
   - **Category**: Boundary (keep)
   - **Context**: Validate CDC Socrata dataset rows array
   - **Decision**: Retained with dataset version comment.
6. **L170 – CdcSocrataAdapter.fetch**: `yield ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Ensure each row is an object before yield
   - **Decision**: Retained.
7. **L249 – WhoGhoAdapter.fetch**: `payload_map = ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Validate WHO GHO response envelope
   - **Decision**: Retained.
8. **L251 – WhoGhoAdapter.fetch**: `for entry in ensure_json_sequence(...)`
   - **Category**: Boundary (keep)
   - **Context**: Iterate over WHO GHO values array
   - **Decision**: Retained.
9. **L252 – WhoGhoAdapter.fetch**: `yield ensure_json_mapping(...)`
   - **Category**: Boundary (keep)
   - **Context**: Promote each WHO GHO entry to mapping
   - **Decision**: Retained.
10. **L260 – WhoGhoAdapter.parse**: `"value": ensure_json_value(raw.get("Value"), ...)`
    - **Category**: Internal redundancy (remove)
    - **Context**: Copy `Value` field into typed payload
    - **Removal criteria**: Replace with helper that normalises scalars/sequences
      without recursive `ensure_json_value` call.
11. **L295 – OpenPrescribingAdapter.fetch**: `rows = ensure_json_sequence(...)`
    - **Category**: Boundary (keep)
    - **Context**: Validate OpenPrescribing dataset rows array
    - **Decision**: Retained.
12. **L297 – OpenPrescribingAdapter.fetch**: `yield ensure_json_mapping(...)`
    - **Category**: Boundary (keep)
    - **Context**: Ensure each row is mapping before yielding typed payload
    - **Decision**: Retained.

## Literature adapters (`src/Medical_KG/ingestion/adapters/literature.py`)

Two redundant parse-time call sites remain in the literature adapters.

1. **L224 – PubMedAdapter.parse**: `raw_map = ensure_json_mapping(raw, ...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Promote already-mapped bootstrap records into mapping
   - **Removal criteria**: Replace with `Mapping` type guard and informative
     error message.
2. **L581 – MedRxivAdapter.parse**: `raw_map = ensure_json_mapping(raw, ...)`
   - **Category**: Internal redundancy (remove)
   - **Context**: Promote typed bootstrap records into mapping
   - **Removal criteria**: Replace with `Mapping` guard and typed fallback.

## Removal Criteria Summary

Internal validation is removed when all of the following hold:

- The value originates from a TypedDict field whose type already encodes the
  expected structure (`JSONMapping`, `Sequence[JSONMapping]`, etc.).
- A preceding `isinstance` check guards optional branches, allowing graceful
  fallback to `{}` / `[]` instead of raising.
- Converting values to payload-friendly forms can be handled by lightweight
  helper functions (`_iter_sequence`, `_as_json_value`) without blanket runtime
  validation.

Remaining `ensure_json_*` calls are restricted to HTTP boundary parsing where
external APIs may return malformed content; inline comments will document the
assumed API versions for maintainers.
