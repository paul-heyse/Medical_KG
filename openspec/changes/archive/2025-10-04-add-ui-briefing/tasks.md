# Implementation Tasks

## 1. Topic Definition Wizard

- [ ] 1.1 Create multi-step wizard (Topic Overview → Clinical Question → Evidence Scope → Deliverable Type)
- [ ] 1.2 Add guided inputs for PICO elements with ontology lookup
- [ ] 1.3 Implement population/intervention auto-suggest using KG entities
- [ ] 1.4 Create topic template library (Drug Evaluation, Device Assessment, Guideline Review)
- [ ] 1.5 Add collaborative topic creation with team member invites

## 2. Evidence Assembly Workspace

- [ ] 2.1 Build `EvidenceWorkspace` with drag-and-drop zones (Included, Excluded, Under Review)
- [ ] 2.2 Integrate with retrieval results allowing direct drag from search
- [ ] 2.3 Add evidence quality scoring (GRADE, evidence level) with badge display
- [ ] 2.4 Create evidence grouping by theme (efficacy, safety, dosing, etc.)
- [ ] 2.5 Implement citation manager with automatic deduplication

## 3. Narrative Synthesis Editor

- [ ] 3.1 Create rich text editor with citation insertion commands
- [ ] 3.2 Add AI-assisted summary generation from selected evidence chunks
- [ ] 3.3 Implement inline span-to-citation linking with hover preview
- [ ] 3.4 Create section templates (Executive Summary, Evidence Review, Recommendations)
- [ ] 3.5 Add comment threads for collaborative review

## 4. Evidence Map Visualization

- [ ] 4.1 Build force-directed evidence map showing study relationships
- [ ] 4.2 Add node sizing by sample size or evidence weight
- [ ] 4.3 Implement edge coloring by outcome type (efficacy, safety, QoL)
- [ ] 4.4 Create interactive drill-down from map node to evidence detail
- [ ] 4.5 Add export of evidence map as publication-ready SVG

## 5. Question Bank Generator

- [ ] 5.1 Create question generator analyzing knowledge gaps in evidence
- [ ] 5.2 Add question type categorization (clarification, deep dive, contradiction)
- [ ] 5.3 Implement question prioritization based on evidence strength
- [ ] 5.4 Create editable question list with manual additions
- [ ] 5.5 Add export to interview guide format (Markdown, DOCX)

## 6. Deliverable Templates

- [ ] 6.1 Build template selector with previews (One-Pager, Full Report, Slide Deck)
- [ ] 6.2 Create PDF report generator with cover page, TOC, citations
- [ ] 6.3 Implement PPTX export with auto-generated slides per section
- [ ] 6.4 Add custom branding configuration (logo, colors, fonts)
- [ ] 6.5 Create Markdown export for integration with documentation systems

## 7. Collaboration & Versioning

- [ ] 7.1 Implement real-time collaborative editing using CRDT or OT
- [ ] 7.2 Add user presence indicators showing active editors
- [ ] 7.3 Create version history with diff viewing and rollback
- [ ] 7.4 Implement approval workflow with reviewer assignment
- [ ] 7.5 Add notification system for comments and approvals

## 8. Backend API

- [ ] 8.1 Create `/api/briefing/topics` CRUD endpoints
- [ ] 8.2 Add `/api/briefing/evidence` endpoints for evidence management
- [ ] 8.3 Implement `/api/briefing/synthesize` POST endpoint for AI summary generation
- [ ] 8.4 Create `/api/briefing/export` POST endpoint supporting PDF/PPTX/DOCX/MD formats
- [ ] 8.5 Add `/api/briefing/collaborate` WebSocket endpoint for real-time editing
- [ ] 8.6 Implement `/api/briefing/questions` POST endpoint for question generation

## 9. Testing & Documentation

- [ ] 9.1 Write unit tests for briefing components
- [ ] 9.2 Add integration tests for briefing API
- [ ] 9.3 Create E2E tests for full briefing workflow (define → assemble → synthesize → export)
- [ ] 9.4 Document briefing builder in `docs/ui_briefing.md` with template examples
