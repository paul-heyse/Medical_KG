# Medical_KG Comprehensive GUI Proposal

## Executive Summary

This document outlines a comprehensive graphical user interface (GUI) for the Medical_KG system, transforming the API-only platform into a full-featured web application for medical knowledge management. The proposed UI consists of six integrated modules supporting the complete workflow from data ingestion through briefing generation.

## Current State

Medical_KG currently provides:

- **Backend Services**: 20+ data source adapters (PubMed, PMC, ClinicalTrials.gov, DailyMed, device registries, guidelines, ontologies)
- **Processing Pipeline**: PDF parsing (MinerU), semantic chunking, embedding generation (Qwen3, SPLADE-v3), multi-stage retrieval, clinical extraction, facet generation
- **Knowledge Graph**: Neo4j-based medical ontology with SHACL validation
- **APIs**: FastAPI endpoints for ingestion, retrieval, extraction, KG writing, and briefing generation
- **No GUI**: All interaction requires API calls or CLI commands

## Proposed UI Architecture

### Technology Stack

**Frontend:**

- **Framework**: React 18+ with TypeScript for type safety and developer productivity
- **Build Tool**: Vite for fast development and optimized production builds
- **Styling**: Tailwind CSS for consistent, responsive design
- **State Management**:
  - Zustand for global UI state (theme, user session, navigation)
  - TanStack Query (React Query) for server state management and caching
- **Routing**: React Router v6 for client-side navigation
- **Data Visualization**:
  - Recharts for charts and metrics
  - react-force-graph for knowledge graph visualization
  - D3.js for custom evidence maps
- **Real-Time**: WebSocket connections for live updates (ingestion progress, collaborative editing)
- **Testing**: Vitest + React Testing Library for unit tests, Playwright for E2E tests

**Backend Integration:**

- **API Client**: Auto-generated TypeScript client from OpenAPI spec
- **Authentication**: JWT tokens with refresh mechanism
- **File Uploads**: Multipart form data with progress tracking
- **WebSocket**: `/ws/*` endpoints for real-time features

**Development Setup:**

- **Dev Server**: Vite with proxy to FastAPI backend (<http://localhost:8000>)
- **Code Quality**: ESLint, Prettier, TypeScript strict mode
- **Documentation**: Storybook for component library

## UI Modules Overview

### 1. Dashboard & Main Interface (`add-ui-dashboard`)

**Purpose**: Primary entry point providing system overview and quick access to all workflows.

**Key Features:**

- Real-time health monitoring for all services (retrieval, extraction, facets, KG, ingestion)
- Activity feed showing last 50 operations with status and user attribution
- Quick action cards for primary workflows (Ingest, Retrieve, Extract, Brief)
- System metrics charts (ingestion volume, query rate, KG growth)
- Global search bar with entity lookup and autocomplete
- User profile management and theme toggle (dark/light mode)
- WCAG 2.1 AA accessibility compliance

**Impact**: Reduces barrier to entry; users can access all functionality without memorizing API endpoints or CLI commands.

### 2. Ingestion Management UI (`add-ui-ingestion`)

**Purpose**: Configure, launch, monitor, and review data ingestion from 20+ sources.

**Key Features:**

- Source catalog displaying all 23 available adapters with filtering
- Multi-step batch ingestion form with source-specific parameter validation
- Real-time progress monitoring via WebSocket (document-level status tracking)
- Ingestion history table with filtering, sorting, and drill-down
- Scheduled ingestion with visual cron builder and calendar preview
- PDF upload interface for manual document ingestion (MinerU pipeline)
- Error analysis and retry functionality for failed ingestions

**User Scenarios:**

- **Clinical Trials Analyst**: "I need to ingest the latest 50 NSCLC trials from ClinicalTrials.gov for an upcoming engagement"
- **Literature Reviewer**: "Upload these 10 PDF guidelines and process them through MinerU"
- **Data Curator**: "Schedule daily PMC ingestion for cancer-related articles"

**Impact**: Eliminates need for command-line access; enables self-service data ingestion with full visibility.

### 3. Retrieval & Search UI (`add-ui-retrieval`)

**Purpose**: Intuitive search interface leveraging multi-stage retrieval with intent-aware ranking.

**Key Features:**

- Google-like search bar with autocomplete and query suggestions
- Intent detection (PICO, Effects, AE, Dose, Eligibility) with facet highlighting
- Faceted navigation sidebar (source, date range, study type, evidence level)
- Result cards with snippet highlighting, metadata, and retrieval score breakdowns
- Query refinement UI showing synonym expansions and fusion logic
- Result actions: expand context, view in document, add to briefing, export citation
- Saved searches and search history with collaborative sharing
- Visual "Explain Mode" showing BM25/SPLADE/Dense/RRF score contributions

**User Scenarios:**

- **Engagement Lead**: "Find all studies on pembrolizumab for NSCLC published in the last 3 years"
- **Medical Analyst**: "What are the hazard ratios for SGLT2 inhibitors in heart failure?"
- **Strategist**: "Show me conflicting evidence about statin efficacy in elderly populations"

**Impact**: Makes sophisticated multi-retrieval accessible to non-technical users; surfaces provenance and scoring logic for transparency.

### 4. Knowledge Graph Explorer (`add-ui-kg-explorer`)

**Purpose**: Visual exploration of the Neo4j medical knowledge graph with relationship navigation.

**Key Features:**

- Interactive force-directed graph visualization with zoom/pan/filter
- Entity search with type-ahead and loading into canvas
- Entity detail panels showing all properties, relationships, and provenance
- Neighborhood expansion (1-hop, 2-hop, 3-hop) with relationship filtering
- Visual query builder for constructing Cypher queries via drag-and-drop
- Path finding between entities with shortest path highlighting
- Subgraph export (JSON, GraphML, Cypher, SVG)
- Graph statistics dashboard (centrality metrics, community detection)

**User Scenarios:**

- **Domain Expert**: "Show me all drugs connected to EGFR mutations and their trial outcomes"
- **Data Validator**: "Verify that NCT12345678 correctly links to its interventions and outcomes"
- **Researcher**: "Find all evidence chains connecting Drug X to Outcome Y"

**Impact**: Makes graph data navigable without Cypher knowledge; enables discovery of non-obvious connections.

### 5. Clinical Extraction Management UI (`add-ui-extraction`)

**Purpose**: Configure, execute, review, and validate structured clinical data extraction.

**Key Features:**

- Chunk selection interface with facet filtering and preview
- Extraction configuration form (type selection, parameter tuning)
- Side-by-side result viewer with span highlighting and structured output
- Manual span editing with inline value correction
- Extraction validation dashboard with confidence scoring
- Bulk approval workflow with quality metrics
- Extraction history and audit trail with version comparison
- Export to KG write format with SHACL pre-validation

**User Scenarios:**

- **Clinical Data Scientist**: "Extract all hazard ratios with confidence intervals from these 50 oncology papers"
- **Quality Reviewer**: "Review low-confidence adverse event extractions and correct spans"
- **KG Curator**: "Approve these 200 validated PICO extractions for graph ingestion"

**Impact**: Reduces manual JSON editing; enables human-in-the-loop validation workflow; ensures data quality before KG write.

### 6. Briefing Builder & Topic Dossier UI (`add-ui-briefing`)

**Purpose**: End-to-end briefing creation from topic definition through deliverable generation.

**Key Features:**

- Topic definition wizard with PICO-structured clinical questions
- Evidence assembly workspace with drag-and-drop organization
- Narrative synthesis editor with AI-assisted summary generation
- Citation management with automatic formatting (BibTeX, AMA, Vancouver)
- Evidence map visualization showing study relationships
- Interview question bank generator based on knowledge gaps
- Deliverable templates (PDF reports, PPTX slides, DOCX, Markdown)
- Real-time collaborative editing with version control
- Multi-stage approval workflow with reviewer assignment

**User Scenarios:**

- **Engagement Prep**: "Create a briefing on CAR-T therapy for multiple myeloma for our meeting next week"
- **Interview Planning**: "Generate interview questions targeting gaps in the efficacy evidence"
- **Deliverable Generation**: "Export this briefing as a 15-slide deck with Mercor branding"

**Impact**: Core value proposition of Medical_KG; transforms evidence into actionable briefings with minimal manual assembly.

## UI Infrastructure & Cross-Cutting Concerns

### Authentication & Authorization

- JWT-based authentication with token refresh
- Role-based access control (Analyst, Lead, Admin)
- License tier enforcement (Public, Member, Affiliate) affecting data visibility
- SSO integration (OAuth2) for enterprise deployments

### Performance & Optimization

- Code splitting by route for faster initial loads
- Lazy loading of heavy components (graph visualizer, chart libraries)
- React.memo and useMemo for expensive computations
- Virtualized lists for large datasets (1000+ items)
- Service worker for offline capability (read-only access to cached data)

### Responsive Design

- Mobile-first approach with breakpoints (768px tablet, 1024px desktop, 1920px wide)
- Collapsible sidebars on smaller screens
- Touch-friendly controls on tablet devices
- Adaptive layout grids (3-column → 2-column → 1-column)

### Accessibility (WCAG 2.1 AA)

- Keyboard navigation for all interactive elements
- ARIA labels and live regions for screen readers
- High-contrast themes with 4.5:1 text ratios
- Focus indicators (3px outline)
- Skip navigation links

### Observability

- Frontend error tracking (Sentry or similar)
- Performance monitoring (Web Vitals: LCP, FID, CLS)
- User analytics (page views, feature usage, session duration)
- API request tracing with correlation IDs

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

1. Project setup (Vite, React, TypeScript, Tailwind)
2. Core layout components (AppShell, Nav, Header, Footer)
3. API client generation from OpenAPI spec
4. Authentication flow (login, token refresh, logout)
5. Dashboard with basic health monitoring

### Phase 2: Core Workflows (Weeks 4-8)

6. Ingestion Management UI (source catalog, batch form, progress monitoring)
7. Retrieval & Search UI (search bar, results, facets, saved searches)
8. Basic result actions (context expansion, citation export)

### Phase 3: Advanced Features (Weeks 9-12)

9. Knowledge Graph Explorer (visualization, entity detail, neighborhood expansion)
10. Extraction Management UI (chunk selection, result viewer, validation dashboard)
11. Integration between modules (search → add to briefing, extraction → KG write)

### Phase 4: Briefing Builder (Weeks 13-16)

12. Topic definition wizard and evidence workspace
13. Narrative synthesis editor with AI integration
14. Evidence map and question generator
15. Deliverable templates and export functionality

### Phase 5: Polish & Launch (Weeks 17-20)

16. Real-time collaboration features (WebSocket, concurrent editing)
17. Version control and approval workflows
18. Comprehensive testing (unit, integration, E2E)
19. Performance optimization and accessibility audit
20. Documentation and user training materials

## Success Metrics

### User Adoption

- **Target**: 80%+ of Medical_KG API users transition to UI within 3 months
- **Measure**: Active UI sessions vs. direct API calls

### Efficiency Gains

- **Target**: 50% reduction in time from data ingestion to briefing delivery
- **Measure**: Average time for "ingest → retrieve → extract → brief" workflow

### Self-Service Enablement

- **Target**: 90% of ingestion and extraction tasks performed via UI without developer intervention
- **Measure**: Ratio of UI-initiated vs. CLI-initiated operations

### User Satisfaction

- **Target**: NPS score of 40+ and SUS (System Usability Scale) score of 75+
- **Measure**: Quarterly user surveys

### Data Quality

- **Target**: 20% improvement in extraction accuracy through human-in-the-loop validation
- **Measure**: Precision/recall metrics on validated extractions vs. fully automated

## Risk Mitigation

### Technical Risks

- **Risk**: Graph visualization performance degrades with large subgraphs (1000+ nodes)
- **Mitigation**: Implement pagination, clustering, and lazy loading; warn users before loading large result sets

- **Risk**: Real-time collaboration conflicts in briefing editor
- **Mitigation**: Use CRDT or Operational Transformation; provide clear conflict resolution UI

- **Risk**: Browser compatibility issues (older IE, Safari quirks)
- **Mitigation**: Define minimum browser versions (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+); use Babel polyfills

### Organizational Risks

- **Risk**: User resistance to new interface (preference for CLI/API)
- **Mitigation**: Provide migration guides; maintain API parity; collect early feedback from power users

- **Risk**: Feature creep extending timeline beyond 20 weeks
- **Mitigation**: Prioritize MVP features; defer advanced visualizations to Phase 6; timebox each phase

### Security Risks

- **Risk**: XSS attacks via user-generated content (comments, briefing text)
- **Mitigation**: Sanitize all user input; use DOMPurify; implement CSP headers

- **Risk**: Unauthorized access to sensitive medical data
- **Mitigation**: Enforce JWT validation on all API calls; implement license tier checks; audit access logs

## OpenSpec Change Proposals

All UI modules have been documented as detailed OpenSpec change proposals:

1. **add-ui-dashboard**: Main interface and system overview (✓ validated)
2. **add-ui-ingestion**: Data source ingestion management (✓ validated)
3. **add-ui-retrieval**: Search and retrieval interface (✓ validated)
4. **add-ui-kg-explorer**: Knowledge graph visualization (✓ validated)
5. **add-ui-extraction**: Clinical data extraction management (✓ validated)
6. **add-ui-briefing**: Briefing builder and topic dossiers (✓ validated)

Each proposal includes:

- **proposal.md**: Rationale, changes, and impact assessment
- **tasks.md**: Detailed implementation checklist (40-50 tasks per module)
- **specs/{capability}/spec.md**: Requirements with scenarios following OpenSpec format

Total: **260+ implementation tasks** across 6 modules with comprehensive requirements coverage.

## Next Steps

1. **Approval Gate**: Review proposals with stakeholders (analysts, leads, PMs)
2. **Design Mockups**: Create high-fidelity mockups for each module in Figma
3. **User Research**: Conduct interviews with 5-10 target users to validate workflows
4. **Technical Spike**: Prototype graph visualization and real-time collaboration to de-risk
5. **Resource Allocation**: Staff Phase 1 team (2 frontend engineers, 1 backend engineer, 1 designer)
6. **Kickoff**: Begin Phase 1 implementation

## Conclusion

This comprehensive UI proposal transforms Medical_KG from an API-only platform into a full-featured application accessible to non-technical users. By covering the complete workflow—from data ingestion through briefing generation—the UI enables Mercor analysts to prepare for participant engagements with unprecedented speed and thoroughness.

The modular architecture allows incremental implementation, with each module delivering standalone value while integrating seamlessly with others. The proposed timeline of 20 weeks balances ambition with feasibility, and the comprehensive OpenSpec documentation ensures implementation fidelity.

**Approval of these proposals unlocks Medical_KG's full potential as a knowledge readiness engine for medical domain mastery.**
