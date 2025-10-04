# UI Briefing Builder & Topic Dossier Specification

## Overview

The Briefing Builder provides end-to-end topic dossier creation from topic definition through evidence assembly, synthesis, and deliverable generation.

## ADDED Requirements

### Requirement: Topic Definition Wizard

The UI SHALL guide users through structured topic creation with clinical question formulation and evidence scope definition.

#### Scenario: Wizard flow

- **WHEN** a user clicks "New Briefing"
- **THEN** a 4-step wizard SHALL launch: Topic Overview → Clinical Question → Evidence Scope → Deliverable Type
- **AND** progress indicators SHALL show current step (1 of 4)
- **AND** "Next" SHALL be disabled until required fields are completed

#### Scenario: PICO-structured question

- **WHEN** a user reaches the Clinical Question step
- **THEN** form fields SHALL prompt for: Population, Intervention, Comparator, Outcome, Context
- **AND** each field SHALL have ontology lookup with auto-suggest
- **AND** selected terms SHALL link to KG entities showing as clickable chips

#### Scenario: Evidence scope configuration

- **WHEN** a user defines evidence scope
- **THEN** options SHALL include: date range, evidence levels, study types, minimum sample size
- **AND** an estimate SHALL show "~X studies, ~Y documents match criteria"
- **AND** clicking "Preview" SHALL run retrieval and show sample results

### Requirement: Evidence Assembly Workspace

The UI SHALL provide a drag-and-drop workspace for organizing retrieved evidence into inclusion/exclusion zones with quality scoring.

#### Scenario: Workspace layout

- **WHEN** a user enters the evidence workspace
- **THEN** three columns SHALL display: "Search & Queue", "Included Evidence", "Excluded Evidence"
- **AND** the search column SHALL show retrieval results with drag handles
- **AND** dragging a result to "Included" SHALL add it to the briefing

#### Scenario: Evidence quality scoring

- **WHEN** evidence is added to "Included"
- **THEN** an automatic GRADE assessment SHALL run (if applicable)
- **AND** a quality badge SHALL display (High/Moderate/Low/Very Low)
- **AND** clicking the badge SHALL show detailed quality criteria

#### Scenario: Evidence grouping

- **WHEN** a user clicks "Group Evidence"
- **THEN** options SHALL appear: by theme (efficacy/safety/dosing), by study design, by outcome type
- **AND** selected grouping SHALL organize evidence into collapsible sections
- **AND** sections SHALL have editable titles and reordering via drag-and-drop

### Requirement: Narrative Synthesis Editor

The UI SHALL provide a rich text editor with AI-assisted synthesis, citation insertion, and collaborative commenting.

#### Scenario: Section templates

- **WHEN** a user clicks "New Section"
- **THEN** template options SHALL appear (Executive Summary, Background, Methods, Results, Discussion, Recommendations)
- **AND** selecting a template SHALL insert pre-structured headings with guidance text
- **AND** templates SHALL adapt to briefing type (drug evaluation vs. guideline review)

#### Scenario: AI-assisted synthesis

- **WHEN** a user selects included evidence and clicks "Generate Summary"
- **THEN** an AI synthesis SHALL generate narrative text citing selected sources
- **AND** citations SHALL insert as inline reference numbers [1, 2]
- **AND** users SHALL be able to edit synthesized text freely

#### Scenario: Citation insertion

- **WHEN** a user types [[
- **THEN** a citation picker SHALL open showing all included evidence
- **AND** selecting an item SHALL insert [[Author Year]] with automatic numbering
- **AND** hovering over citation SHALL show preview tooltip with title and key details

#### Scenario: Collaborative comments

- **WHEN** a user highlights text and clicks "Comment"
- **THEN** a comment thread SHALL open attached to that span
- **AND** other collaborators SHALL see comment indicators (yellow highlights)
- **AND** resolving a comment SHALL remove the highlight

### Requirement: Evidence Map Visualization

The UI SHALL generate an interactive evidence map showing relationships between studies, interventions, and outcomes.

#### Scenario: Evidence map generation

- **WHEN** a user clicks "View Evidence Map"
- **THEN** a force-directed graph SHALL render showing studies as nodes
- **AND** nodes SHALL connect via outcome relationships
- **AND** node size SHALL scale with sample size or evidence weight
- **AND** edge color SHALL indicate outcome direction (positive=green, negative=red, neutral=gray)

#### Scenario: Map interactions

- **WHEN** a user clicks a study node
- **THEN** a detail panel SHALL show study summary and outcomes
- **AND** double-clicking SHALL navigate to full study in document viewer
- **AND** users SHALL be able to export map as high-resolution SVG or PNG

### Requirement: Interview Question Bank Generation

The UI SHALL analyze included evidence to generate interview questions targeting knowledge gaps and uncertainties.

#### Scenario: Automatic question generation

- **WHEN** a user clicks "Generate Questions"
- **THEN** the system SHALL analyze evidence for: gaps (missing comparisons), conflicts (contradictory findings), uncertainties (low confidence)
- **AND** questions SHALL generate for each gap/conflict/uncertainty
- **AND** questions SHALL categorize as: Clarification, Deep Dive, Contradiction Resolution, Future Direction

#### Scenario: Question editing and prioritization

- **WHEN** generated questions appear
- **THEN** users SHALL be able to edit question text
- **AND** drag-and-drop SHALL reorder by priority
- **AND** questions SHALL link to relevant evidence triggering them

#### Scenario: Export to interview guide

- **WHEN** a user clicks "Export Questions"
- **THEN** format options SHALL include Markdown, DOCX, PDF
- **AND** export SHALL include: question text, rationale, relevant evidence references, suggested follow-ups

### Requirement: Deliverable Generation

The UI SHALL support exporting briefings in multiple formats (PDF report, PPTX slides, DOCX, Markdown) with custom branding.

#### Scenario: Template selection

- **WHEN** a user clicks "Generate Deliverable"
- **THEN** template options SHALL display: One-Pager, Full Report (10-20 pages), Slide Deck (15-25 slides), Technical Deep Dive
- **AND** previews SHALL show sample layouts
- **AND** selecting a template SHALL populate with briefing content

#### Scenario: PDF report generation

- **WHEN** a user generates a PDF report
- **THEN** the PDF SHALL include: cover page with topic and date, table of contents, executive summary, evidence sections, references, appendices
- **AND** citations SHALL format as superscript numbers with reference list at end
- **AND** custom branding (logo, colors) SHALL apply from organization settings

#### Scenario: PowerPoint export

- **WHEN** a user generates a slide deck
- **THEN** slides SHALL auto-generate: title slide, executive summary (1-2 slides), evidence overview (1 slide), detailed findings (1 slide per major section), recommendations, references
- **AND** evidence tables and charts SHALL convert to PowerPoint objects
- **AND** speaker notes SHALL include expanded details and source attributions

### Requirement: Version Control and Approval Workflow

The UI SHALL track briefing versions with diff viewing, rollback capability, and multi-stage approval workflow.

#### Scenario: Version saving

- **WHEN** a user makes changes to a briefing
- **THEN** autosave SHALL trigger every 30 seconds
- **AND** clicking "Save Version" SHALL create a named snapshot
- **AND** version list SHALL show: version number, timestamp, author, change summary

#### Scenario: Diff viewing

- **WHEN** a user compares two versions
- **THEN** a side-by-side diff SHALL highlight: added text (green), removed text (red), modified text (yellow)
- **AND** evidence additions/removals SHALL show in separate diff panel

#### Scenario: Approval workflow

- **WHEN** a briefing is ready for review
- **THEN** owner SHALL assign reviewers with roles (Peer Reviewer, Domain Expert, Final Approver)
- **AND** reviewers SHALL receive notifications
- **AND** reviewers SHALL approve/request changes with comments
- **AND** status SHALL progress: Draft → Under Review → Approved → Published

### Requirement: Real-Time Collaboration

Multiple users SHALL be able to edit briefings simultaneously with conflict resolution and change attribution.

#### Scenario: Collaborative editing

- **WHEN** two users edit the same briefing
- **THEN** both users SHALL see each other's cursors with name labels
- **AND** changes SHALL sync in real-time (within 500ms)
- **AND** concurrent edits to different sections SHALL merge automatically

#### Scenario: Conflict resolution

- **WHEN** two users edit the same text simultaneously
- **THEN** a conflict modal SHALL appear showing both versions
- **AND** users SHALL be able to choose one version or merge manually
- **AND** resolved conflicts SHALL log to version history
