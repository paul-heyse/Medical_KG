# Medical_KG GUI Proposals - Quick Reference

## Overview

A comprehensive graphical user interface has been proposed for Medical_KG across **6 major modules**, totaling **260+ implementation tasks** and **20 weeks** of development effort.

## Proposal Summary

| Module | Change ID | Tasks | Status | Priority |
|--------|-----------|-------|--------|----------|
| Dashboard & Main Interface | `add-ui-dashboard` | 28 | ✓ Validated | P0 - Foundation |
| Ingestion Management | `add-ui-ingestion` | 40 | ✓ Validated | P1 - Core |
| Retrieval & Search | `add-ui-retrieval` | 42 | ✓ Validated | P1 - Core |
| Knowledge Graph Explorer | `add-ui-kg-explorer` | 44 | ✓ Validated | P2 - Advanced |
| Extraction Management | `add-ui-extraction` | 34 | ✓ Validated | P2 - Advanced |
| Briefing Builder | `add-ui-briefing` | 45 | ✓ Validated | P3 - Deliverables |

**Total**: 6 modules, 233 tasks, all proposals validated with `openspec validate --strict`

## File Locations

### Proposals

```
openspec/changes/
├── add-ui-dashboard/
│   ├── proposal.md          # Dashboard rationale and impact
│   ├── tasks.md             # 28 implementation tasks
│   └── specs/ui-dashboard/spec.md  # 9 requirements, 27 scenarios
├── add-ui-ingestion/
│   ├── proposal.md          # Ingestion UI rationale
│   ├── tasks.md             # 40 implementation tasks
│   └── specs/ui-ingestion/spec.md  # 8 requirements, 24+ scenarios
├── add-ui-retrieval/
│   ├── proposal.md          # Search UI rationale
│   ├── tasks.md             # 42 implementation tasks
│   └── specs/ui-retrieval/spec.md  # 7 requirements, 21+ scenarios
├── add-ui-kg-explorer/
│   ├── proposal.md          # Graph explorer rationale
│   ├── tasks.md             # 44 implementation tasks
│   └── specs/ui-kg-explorer/spec.md  # 8 requirements, 24+ scenarios
├── add-ui-extraction/
│   ├── proposal.md          # Extraction UI rationale
│   ├── tasks.md             # 34 implementation tasks
│   └── specs/ui-extraction/spec.md  # 7 requirements, 21+ scenarios
└── add-ui-briefing/
    ├── proposal.md          # Briefing builder rationale
    ├── tasks.md             # 45 implementation tasks
    └── specs/ui-briefing/spec.md  # 8 requirements, 24+ scenarios
```

### Documentation

```
docs/
├── UI_PROPOSAL_SUMMARY.md   # Comprehensive overview (this should be your starting point)
└── UI_PROPOSALS_INDEX.md    # This file - quick reference
```

## Key Technologies

**Frontend Stack:**

- React 18+ with TypeScript
- Vite build tool
- Tailwind CSS for styling
- TanStack Query for server state
- React Router v6 for navigation
- Recharts + D3.js for visualizations
- react-force-graph for KG visualization

**Backend Integration:**

- Auto-generated TypeScript API client from OpenAPI
- WebSocket for real-time updates
- JWT authentication

**Development:**

- Vitest + React Testing Library
- Playwright for E2E tests
- Storybook for component documentation
- ESLint + Prettier

## Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

- Project setup and core layout
- Authentication and API client
- Basic dashboard

### Phase 2: Core Workflows (Weeks 4-8)

- **add-ui-ingestion**: Full ingestion management
- **add-ui-retrieval**: Search and retrieval interface

### Phase 3: Advanced Features (Weeks 9-12)

- **add-ui-kg-explorer**: Graph visualization
- **add-ui-extraction**: Extraction management
- Integration between modules

### Phase 4: Briefing Builder (Weeks 13-16)

- **add-ui-briefing**: Complete briefing workflow

### Phase 5: Polish & Launch (Weeks 17-20)

- Real-time collaboration
- Performance optimization
- Comprehensive testing
- User documentation

## Quick Commands

```bash
# View all UI proposals
openspec list | grep add-ui

# Validate all proposals
openspec validate add-ui-dashboard --strict
openspec validate add-ui-ingestion --strict
openspec validate add-ui-retrieval --strict
openspec validate add-ui-kg-explorer --strict
openspec validate add-ui-extraction --strict
openspec validate add-ui-briefing --strict

# View specific proposal details
openspec show add-ui-dashboard
openspec show add-ui-ingestion

# View specifications
openspec show ui-dashboard --type spec
openspec show ui-ingestion --type spec
```

## User Scenarios by Persona

### Medical Analyst

- **Primary**: Retrieval UI, Extraction UI, Briefing Builder
- **Workflow**: Search literature → Extract clinical data → Build briefing
- **Time savings**: 50% reduction (from 8 hours to 4 hours for typical briefing)

### Engagement Lead

- **Primary**: Dashboard, Briefing Builder, KG Explorer
- **Workflow**: Review system status → Explore entity connections → Generate deliverables
- **Value**: Self-service access to all system capabilities

### Data Curator

- **Primary**: Ingestion UI, KG Explorer, Extraction UI
- **Workflow**: Schedule ingestions → Validate graph data → Review extraction quality
- **Impact**: 90% reduction in CLI usage

### Strategist/PM

- **Primary**: Dashboard, Briefing Builder
- **Workflow**: Monitor overall activity → Review briefings → Approve deliverables
- **Benefit**: High-level oversight without technical expertise

## Key Features Highlights

### Dashboard

- Real-time health monitoring for all services
- Activity feed with last 50 operations
- Global search across entities
- Quick actions for primary workflows

### Ingestion

- 20+ source adapters with visual catalog
- Real-time progress tracking (WebSocket)
- Scheduled jobs with cron builder
- PDF upload for MinerU pipeline

### Retrieval

- Google-like search with autocomplete
- Intent detection (PICO/Effects/AE/Dose/Eligibility)
- Multi-stage fusion with score explanation
- Saved searches and query refinement

### KG Explorer

- Force-directed graph visualization
- Neighborhood expansion (1-3 hops)
- Visual Cypher query builder
- Subgraph export (JSON/GraphML/Cypher/SVG)

### Extraction

- Chunk selection with facet filtering
- Side-by-side span highlighting
- Manual correction workflow
- Bulk approval with validation metrics

### Briefing Builder

- Topic definition wizard (PICO-structured)
- Evidence assembly workspace (drag-and-drop)
- AI-assisted narrative synthesis
- Deliverable generation (PDF/PPTX/DOCX/MD)
- Real-time collaboration

## Success Metrics

- **User Adoption**: 80%+ UI usage within 3 months
- **Efficiency**: 50% faster briefing creation
- **Self-Service**: 90% of operations via UI (not CLI)
- **Satisfaction**: NPS 40+, SUS 75+
- **Quality**: 20% improvement in extraction accuracy

## Next Steps for Implementation

1. **Stakeholder Review** (Week 0):
   - Present `docs/UI_PROPOSAL_SUMMARY.md` to leadership
   - Gather feedback from target users (5-10 interviews)
   - Prioritize features if timeline needs compression

2. **Design Phase** (Weeks 1-2):
   - Create Figma mockups for each module
   - User testing with clickable prototypes
   - Finalize design system (colors, typography, spacing)

3. **Development Kickoff** (Week 3):
   - Staff team (2 frontend, 1 backend, 1 designer)
   - Set up development environment
   - Begin Phase 1 implementation

4. **Iterative Development** (Weeks 3-20):
   - 2-week sprints with demos
   - Continuous user feedback
   - Adjust priorities based on learnings

## Questions or Clarifications?

**Architecture**: See `docs/UI_PROPOSAL_SUMMARY.md` "UI Infrastructure" section
**Specific Module**: Read individual `openspec/changes/add-ui-*/proposal.md` files
**Implementation Details**: Review `openspec/changes/add-ui-*/tasks.md` checklists
**Requirements**: Study `openspec/changes/add-ui-*/specs/*/spec.md` specifications

---

**Status**: All 6 proposals validated and ready for stakeholder review ✓
**Last Updated**: October 3, 2025
**Prepared By**: AI Assistant per user request for comprehensive GUI proposal
