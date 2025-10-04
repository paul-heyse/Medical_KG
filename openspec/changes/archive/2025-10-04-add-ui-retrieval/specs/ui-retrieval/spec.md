# UI Retrieval & Search Specification

## Overview

The Retrieval UI provides an intuitive search interface for multi-stage retrieval with intent detection, faceted navigation, and result exploration.

## ADDED Requirements

### Requirement: Search Input with Autocomplete

The search interface SHALL provide real-time autocomplete suggestions based on entity names, previous queries, and ontology terms.

#### Scenario: Autocomplete suggestions

- **WHEN** a user types at least 3 characters in the search bar
- **THEN** a dropdown SHALL appear within 200ms showing up to 10 suggestions
- **AND** suggestions SHALL be grouped by type (Entities, Recent Queries, Ontology Terms)
- **AND** arrow keys SHALL navigate suggestions and Enter SHALL select

#### Scenario: Query execution

- **WHEN** a user submits a search query
- **THEN** the UI SHALL display loading indicator
- **AND** results SHALL appear within 2 seconds for typical queries
- **AND** query SHALL be added to search history

### Requirement: Intent-Aware Results

The UI SHALL automatically detect query intent (PICO/Effects/AE/Dose/Eligibility) and highlight relevant facets in results.

#### Scenario: Effects intent detection

- **WHEN** a user searches "pembrolizumab survival benefit NSCLC"
- **THEN** an "Effects" intent badge SHALL display above results
- **AND** hazard ratios, confidence intervals, and p-values SHALL highlight in gold within snippets
- **AND** facet sidebar SHALL emphasize study type and endpoint filters

#### Scenario: Manual intent override

- **WHEN** a user clicks the intent badge and selects different intent
- **THEN** results SHALL re-rank based on new intent
- **AND** highlighting SHALL update to match new intent focus

### Requirement: Faceted Navigation

The UI SHALL provide multi-select faceted filters with dynamic count updates and "AND"/"OR" logic.

#### Scenario: Facet filtering

- **WHEN** a user selects multiple source types in facet sidebar
- **THEN** results SHALL filter to show only documents from selected sources
- **AND** other facet counts SHALL update to reflect filtered result set
- **AND** active filters SHALL display as removable chips above results

#### Scenario: Date range facet

- **WHEN** a user adjusts the date range slider
- **THEN** results SHALL update to show only documents within selected range
- **AND** the slider SHALL show distribution histogram of documents by year

### Requirement: Result Cards with Actions

Each result card SHALL display chunk text, metadata, scores, and action buttons for context expansion, document viewing, and citation export.

#### Scenario: Result card display

- **WHEN** search results appear
- **THEN** each result card SHALL show: snippet with highlighted query terms, source icon, publication date, relevance score, and facet badges
- **AND** hovering over score SHALL show tooltip with BM25/SPLADE/Dense breakdown

#### Scenario: Context expansion

- **WHEN** a user clicks "Show Context" on a result
- **THEN** the card SHALL expand showing ±2 neighboring chunks
- **AND** the expanded section SHALL have subtle background differentiation
- **AND** "Collapse" button SHALL restore original view

#### Scenario: Citation export

- **WHEN** a user clicks "Export Citation"
- **THEN** a modal SHALL appear with format options (BibTeX, RIS, AMA, Vancouver, Chicago)
- **AND** selecting a format SHALL copy formatted citation to clipboard
- **AND** a success toast SHALL confirm "Citation copied"

### Requirement: Query Refinement

The UI SHALL provide query analysis showing synonym expansions, ontology mappings, and score explanation with refinement controls.

#### Scenario: Query analysis display

- **WHEN** a user enables "Explain Query" mode
- **THEN** a refinement panel SHALL appear showing: original query, expanded terms with weights, applied filters, and retriever settings
- **AND** synonym chips SHALL be removable to exclude specific expansions

#### Scenario: Reranking toggle

- **WHEN** a user enables reranking
- **THEN** results SHALL re-sort with reranker scores
- **AND** a "Reranking" badge SHALL appear on affected results
- **AND** hover tooltip SHALL show reranker confidence

### Requirement: Saved Searches

Users SHALL be able to save searches with filters for quick re-execution and collaborative sharing.

#### Scenario: Save search

- **WHEN** a user clicks "Save Search" after executing a query
- **THEN** a modal SHALL prompt for search name and description
- **AND** upon save, the search SHALL appear in the saved searches sidebar
- **AND** a unique shareable link SHALL be generated

#### Scenario: Load saved search

- **WHEN** a user clicks a saved search from sidebar
- **THEN** the search bar SHALL populate with saved query
- **AND** all saved filters SHALL apply automatically
- **AND** results SHALL load as if manually entered

### Requirement: Explain Mode

The UI SHALL provide detailed score explanations showing contribution of each retriever (BM25, SPLADE, Dense, RRF) to final scores.

#### Scenario: Enable explain mode

- **WHEN** a user toggles "Explain Scores"
- **THEN** each result card SHALL expand showing score breakdown table
- **AND** table SHALL show: BM25 score, SPLADE score, Dense score, RRF position, Rerank score (if enabled), Final score
- **AND** bars SHALL visualize relative contribution of each component
