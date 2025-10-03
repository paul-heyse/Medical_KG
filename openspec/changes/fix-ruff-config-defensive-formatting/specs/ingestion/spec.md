# Briefing System Robustness Delta

## MODIFIED Requirements

### Requirement: Briefing Generation Resilience

The briefing system SHALL handle partial or incomplete data gracefully without crashing, providing sensible defaults for missing fields and logging warnings for data quality issues.

#### Scenario: Missing section titles

- **WHEN** a briefing section payload lacks a 'title' field
- **THEN** the formatter SHALL use 'Untitled Section' as default
- **AND** SHALL log a warning about the missing field
- **AND** SHALL continue generating the briefing without errors

#### Scenario: Missing citation metadata

- **WHEN** a citation payload lacks 'doc_id' or 'citation_count' fields
- **THEN** the formatter SHALL use 'Unknown' for doc_id and 0 for citation_count
- **AND** SHALL log warnings about missing metadata
- **AND** SHALL complete HTML/PDF generation successfully

#### Scenario: Empty content items

- **WHEN** a briefing item has an empty or missing 'content' field
- **THEN** the formatter SHALL skip the item or render empty placeholder
- **AND** SHALL continue processing remaining items
- **AND** SHALL not raise KeyError or similar exceptions
