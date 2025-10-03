# UI Clinical Extraction Management Specification

## Overview

The Extraction Management UI enables configuration, execution, review, and validation of structured clinical data extraction from document chunks.

## ADDED Requirements

### Requirement: Chunk Selection Interface

The UI SHALL provide a searchable, filterable interface for selecting chunks for extraction with preview and metadata display.

#### Scenario: Chunk browser

- **WHEN** a user navigates to `/ui/extraction`
- **THEN** a grid of chunk cards SHALL display with pagination
- **AND** each card SHALL show: chunk text preview (first 200 chars), document title, section, facet type badges, and checkbox
- **AND** multi-select SHALL be enabled via checkboxes with "Select All" option

#### Scenario: Facet-based filtering

- **WHEN** a user filters by facet type "Effects"
- **THEN** only chunks with Effects facets SHALL display
- **AND** filter count SHALL update "Showing 42 of 1,234 chunks"

#### Scenario: Bulk import from retrieval

- **WHEN** a user clicks "Import from Search"
- **THEN** a modal SHALL open with search interface
- **AND** retrieval results SHALL display with "Add All" and "Add Selected" buttons
- **AND** added chunks SHALL appear in extraction queue

### Requirement: Extraction Configuration

The UI SHALL provide a configuration form for extraction type selection, parameter tuning, and model settings.

#### Scenario: Extraction type selection

- **WHEN** a user selects extraction type from dropdown (PICO, Effects, AE, Dose, Eligibility)
- **THEN** type-specific parameter fields SHALL appear
- **AND** for Effects, fields SHALL include: outcome types, effect measure types (HR/RR/OR), confidence threshold
- **AND** a description SHALL explain what will be extracted

#### Scenario: Test extraction

- **WHEN** a user clicks "Test on Sample" with 1 chunk selected
- **THEN** extraction SHALL run on that chunk only
- **AND** results SHALL preview in modal showing extracted fields and spans
- **AND** users SHALL approve config or adjust parameters and retest

### Requirement: Result Viewer with Span Highlighting

The UI SHALL display extraction results side-by-side with source chunks showing span highlighting and structured output.

#### Scenario: Side-by-side layout

- **WHEN** extraction results load
- **THEN** left pane SHALL show chunk text with spans highlighted in colors by field type
- **AND** right pane SHALL show extracted structured data in expandable JSON tree
- **AND** panes SHALL scroll synchronously maintaining span-to-data alignment

#### Scenario: Span hover tooltips

- **WHEN** a user hovers over a highlighted span
- **THEN** a tooltip SHALL show: extracted field name, extracted value, confidence score, character offsets
- **AND** clicking the span SHALL highlight corresponding field in JSON tree

#### Scenario: Confidence visualization

- **WHEN** extraction results display
- **THEN** low-confidence extractions (<0.7) SHALL have yellow warning badges
- **AND** very low confidence (<0.5) SHALL have red error badges
- **AND** confidence histogram SHALL show distribution across all extractions

### Requirement: Manual Span Editing

Users SHALL be able to adjust span boundaries, edit extracted values, and re-extract with corrected spans.

#### Scenario: Span boundary adjustment

- **WHEN** a user enables "Edit Mode" and clicks a span
- **THEN** draggable handles SHALL appear at span start and end
- **AND** dragging handles SHALL update the span boundaries
- **AND** the extracted value SHALL update from new span text

#### Scenario: Value correction

- **WHEN** a user double-clicks an extracted value in the JSON tree
- **THEN** an inline editor SHALL appear
- **AND** after editing, the value SHALL update and mark as "Manually Corrected"
- **AND** a "Re-extract" button SHALL appear to regenerate from corrected span

#### Scenario: Missing extraction addition

- **WHEN** a user selects text in chunk that wasn't extracted
- **THEN** a context menu SHALL appear with "Add as Extraction" option
- **AND** selecting it SHALL open a form to specify field type and value
- **AND** the new extraction SHALL add to JSON tree marked as "Manual Addition"

### Requirement: Validation Dashboard

The UI SHALL provide an aggregate view of extraction quality metrics with filtering for review prioritization.

#### Scenario: Quality metrics display

- **WHEN** a user views the validation dashboard after batch extraction
- **THEN** metrics SHALL show: total extractions, average confidence, missing field percentage, conflict count
- **AND** charts SHALL display: confidence distribution histogram, field coverage heatmap, error type breakdown

#### Scenario: Review prioritization

- **WHEN** a user sorts extractions by confidence
- **THEN** lowest-confidence extractions SHALL appear first
- **AND** filtering by "Missing Required Fields" SHALL show incomplete extractions
- **AND** filtering by "Conflicts" SHALL show extractions with contradictory values

#### Scenario: Bulk approval workflow

- **WHEN** a user selects multiple validated extractions
- **THEN** a "Bulk Approve" button SHALL become enabled
- **AND** clicking it SHALL mark all as "Approved" and enable KG write
- **AND** approved extractions SHALL display green checkmark badges

### Requirement: Extraction History and Audit Trail

The UI SHALL maintain a history of all extractions with versioning, user attribution, and rollback capability.

#### Scenario: Extraction history view

- **WHEN** a user views history for a specific chunk
- **THEN** a timeline SHALL show all extraction attempts with timestamps and users
- **AND** each entry SHALL display: extraction type, version, approver, status (pending/approved/rejected)
- **AND** clicking an entry SHALL load that extraction version

#### Scenario: Comparison view

- **WHEN** a user selects two extraction versions
- **THEN** a diff view SHALL highlight changes between versions
- **AND** added fields SHALL show in green, removed in red, modified in yellow
- **AND** users SHALL be able to "Restore Previous Version"

### Requirement: Export to Knowledge Graph

Approved extractions SHALL be exportable to KG write format with batch submission capability.

#### Scenario: KG export preparation

- **WHEN** a user clicks "Export to KG" with approved extractions selected
- **THEN** a preview modal SHALL show generated KG nodes and relationships
- **AND** SHACL validation SHALL run and display any errors
- **AND** users SHALL be able to fix errors before submission

#### Scenario: Batch KG write

- **WHEN** a user submits valid extractions to KG
- **THEN** a POST request SHALL be made to `/kg/write` with batch payload
- **AND** progress bar SHALL show write status
- **AND** success/failure counts SHALL display with links to KG explorer for written entities
