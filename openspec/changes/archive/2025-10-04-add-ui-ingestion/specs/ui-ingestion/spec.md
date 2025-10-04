# UI Ingestion Management Specification

## Overview

The Ingestion Management UI enables users to configure, launch, monitor, and review data ingestion from 20+ medical knowledge sources through a visual interface.

## ADDED Requirements

### Requirement: Source Catalog Display

The UI SHALL display a comprehensive catalog of all available ingestion source adapters with search, filtering, and detailed documentation.

#### Scenario: View available sources

- **WHEN** a user navigates to `/ui/ingestion`
- **THEN** a grid of source cards SHALL display showing all adapters from the registry
- **AND** each card SHALL show source icon, name, category, and one-line description
- **AND** cards SHALL be organized by category tabs (Literature, Clinical Trials, Guidelines, Ontologies, Devices, Registries)

#### Scenario: Source filtering

- **WHEN** a user types in the source search box
- **THEN** cards SHALL filter in real-time by name, category, or keyword match
- **AND** filter count SHALL update ("Showing 3 of 23 sources")

#### Scenario: Source details

- **WHEN** a user clicks "Details" on a source card
- **THEN** a modal SHALL open displaying full adapter documentation
- **AND** the modal SHALL show required parameters, optional parameters, example values, and rate limits
- **AND** an "Ingest from This Source" button SHALL navigate to the ingestion form

### Requirement: Batch Ingestion Form

The UI SHALL provide a multi-step wizard form for configuring batch ingestions with source-specific parameter validation and preview.

#### Scenario: Form initialization

- **WHEN** a user clicks "Ingest" on a source card
- **THEN** a multi-step form SHALL appear with steps: Source Confirm → Parameters → Preview → Submit
- **AND** step 1 SHALL display the selected source with ability to change
- **AND** step 2 SHALL render dynamic form fields based on adapter schema

#### Scenario: Parameter input for ClinicalTrials.gov

- **WHEN** a user selects "clinicaltrials" source
- **THEN** parameter fields SHALL include "NCT IDs" (textarea), "Study Type" (dropdown), "Date Range" (date pickers)
- **AND** "NCT IDs" SHALL accept comma-separated, newline-separated, or single IDs
- **AND** validation SHALL occur on blur checking NCT format (NCT followed by 8 digits)

#### Scenario: Bulk parameter input

- **WHEN** a user clicks "Bulk Import" on a parameter field
- **THEN** options SHALL appear for "CSV Upload", "NDJSON Paste", "Plain Text"
- **AND** selecting CSV SHALL open file picker accepting .csv and .xlsx files
- **AND** after upload, a preview table SHALL show parsed records with validation status

#### Scenario: Validation errors

- **WHEN** a user enters invalid parameters
- **THEN** inline error messages SHALL appear below the field in red
- **AND** the "Next" button SHALL remain disabled until all errors are resolved
- **AND** a validation summary SHALL show count of errors at the top

#### Scenario: Preview step

- **WHEN** a user advances to the preview step with valid parameters
- **THEN** a summary SHALL show: source name, parameter count, estimated documents, idempotency key
- **AND** a table SHALL list all documents to be ingested with identifier and estimated status
- **AND** users SHALL be able to remove individual documents before submission

#### Scenario: Submission

- **WHEN** a user clicks "Start Ingestion"
- **THEN** a POST request SHALL be made to `/api/ingestion/jobs` with parameters
- **AND** upon success, the user SHALL be redirected to `/ui/ingestion/jobs/{job_id}`
- **AND** the progress monitor SHALL automatically load

### Requirement: Real-Time Progress Monitoring

The UI SHALL display live ingestion progress with document-level status tracking, metrics, and error reporting via WebSocket updates.

#### Scenario: Progress display

- **WHEN** a user views an active ingestion job at `/ui/ingestion/jobs/{job_id}`
- **THEN** an overall progress bar SHALL show percentage complete with animated fill
- **AND** below the bar, metrics SHALL display: completed count, failed count, elapsed time, throughput (docs/sec)
- **AND** a document status grid SHALL show each document with state indicator (queued/fetching/parsing/writing/done/failed)

#### Scenario: WebSocket updates

- **WHEN** the backend emits job progress events
- **THEN** the UI SHALL receive updates within 500ms via WebSocket connection
- **AND** progress bar and metrics SHALL update smoothly without page refresh
- **AND** document grid cells SHALL transition state with color change animation

#### Scenario: Error handling

- **WHEN** documents fail during ingestion
- **THEN** failed documents SHALL display with red indicator and error icon
- **AND** clicking a failed document SHALL expand an error panel showing error message, stack trace, and "Retry" button
- **AND** an error summary section SHALL list all failures grouped by error type

#### Scenario: Job controls

- **WHEN** a user views an in-progress job
- **THEN** "Pause", "Cancel", and "View Logs" buttons SHALL be available
- **AND** clicking "Pause" SHALL suspend fetching without losing progress
- **AND** clicking "Cancel" SHALL show confirmation modal and abort remaining documents

### Requirement: Ingestion History

The UI SHALL provide a searchable, filterable history of all ingestion jobs with drill-down capability to document-level details.

#### Scenario: History table display

- **WHEN** a user navigates to `/ui/ingestion/history`
- **THEN** a paginated table SHALL display with columns: Job ID, Source, Started, Documents, Success Rate, Duration, Status
- **AND** rows SHALL be sorted by start time (most recent first) by default
- **AND** pagination controls SHALL allow navigation through 20 rows per page

#### Scenario: Filtering

- **WHEN** a user applies filters (date range, source, status)
- **THEN** the table SHALL update to show only matching jobs
- **AND** active filters SHALL display as removable chips above the table
- **AND** filter state SHALL persist in URL query parameters

#### Scenario: Row expansion

- **WHEN** a user clicks the expand icon on a job row
- **THEN** the row SHALL expand showing a mini-table of all documents in that job
- **AND** each document SHALL show: ID, status, error (if failed), retry count, timestamps
- **AND** clicking a document ID SHALL navigate to the document detail page

#### Scenario: Bulk actions

- **WHEN** a user selects multiple jobs via checkboxes
- **THEN** a bulk action bar SHALL appear with "Retry Failed", "Export", "Delete" options
- **AND** clicking "Retry Failed" SHALL create new jobs for all failed documents
- **AND** clicking "Export" SHALL download a CSV containing all selected job details

### Requirement: Scheduled Ingestion

The UI SHALL support configuring recurring ingestion jobs with cron-based scheduling and calendar preview.

#### Scenario: Schedule creation

- **WHEN** a user clicks "Schedule Ingestion" from the source catalog
- **THEN** the ingestion form SHALL include an additional "Schedule" step
- **AND** the schedule step SHALL provide a visual cron builder with presets (Daily, Weekly, Monthly, Custom)
- **AND** a calendar preview SHALL show the next 10 scheduled run times

#### Scenario: Schedule management

- **WHEN** a user navigates to `/ui/ingestion/schedules`
- **THEN** a list SHALL display all configured scheduled jobs
- **AND** each schedule SHALL show: name, source, cron expression, next run, enabled status
- **AND** users SHALL be able to enable/disable schedules with a toggle switch

#### Scenario: Schedule run history

- **WHEN** a user clicks on a scheduled job
- **THEN** a detail view SHALL open showing the schedule configuration and run history
- **AND** run history SHALL link back to ingestion history for each execution
- **AND** users SHALL be able to edit schedule parameters or delete the schedule

### Requirement: PDF Upload Interface

The UI SHALL provide a drag-and-drop file uploader for PDF documents with MinerU GPU pipeline integration.

#### Scenario: PDF upload

- **WHEN** a user navigates to `/ui/ingestion/pdf-upload`
- **THEN** a large drag-and-drop zone SHALL be displayed
- **AND** users SHALL be able to drag PDF files or click to open file picker
- **AND** multiple PDF files SHALL be accepted (up to 50 files, 100MB each)

#### Scenario: Upload progress

- **WHEN** a user uploads PDF files
- **THEN** each file SHALL display with a progress bar showing upload percentage
- **AND** after upload completes, a "Processing" indicator SHALL show GPU pipeline status
- **AND** upon completion, each PDF SHALL link to its generated IR document
- **AND** failed uploads SHALL show error message with "Retry" button

### Requirement: Parameter Validation

The UI SHALL validate ingestion parameters client-side before submission with format checking and duplicate detection.

#### Scenario: NCT ID validation

- **WHEN** a user enters NCT IDs in the ClinicalTrials form
- **THEN** each ID SHALL be validated against pattern NCT\d{8}
- **AND** invalid IDs SHALL highlight in red with error message "Invalid NCT format"
- **AND** duplicate IDs within the same batch SHALL warn "Duplicate detected"

#### Scenario: Date range validation

- **WHEN** a user selects a date range
- **THEN** the end date SHALL not be before the start date
- **AND** selecting an end date before start SHALL show error "End date must be after start date"
- **AND** date range SHALL not exceed 10 years (configurable per source)

#### Scenario: File format validation

- **WHEN** a user uploads a CSV for bulk import
- **THEN** the file SHALL be parsed and validated for required columns
- **AND** rows with missing required fields SHALL highlight in preview table
- **AND** a summary SHALL show "X of Y rows valid" with option to "Import Valid Rows Only"
