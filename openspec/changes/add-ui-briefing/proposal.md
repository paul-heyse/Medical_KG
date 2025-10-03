# Change Proposal: Briefing Builder & Topic Dossier UI

## Why

Medical_KG's primary output is briefing-quality topic dossiers for Mercor analysts preparing for participant engagements. Users need a guided interface to define topics, assemble evidence from retrieval/extraction, synthesize narrative summaries, generate question banks, and export polished deliverables without manual document assembly.

## What Changes

- Create topic definition wizard with guided input for clinical questions, populations, interventions
- Build evidence assembly workspace with drag-and-drop from search results and extractions
- Implement narrative synthesis editor with AI-assisted summary generation and citation insertion
- Add evidence map visualization showing relationships between studies, outcomes, and interventions
- Provide question bank generator creating interview questions from knowledge gaps
- Create deliverable templates (PDF reports, slide decks, one-pagers) with customizable branding
- Add collaborative editing with real-time updates and comment threads
- Implement version control for briefing revisions and approval workflows
- Provide export options (PDF, PPTX, DOCX, Markdown) with citation management

## Impact

**Affected specs:** NEW `ui-briefing` capability

**Affected code:**

- NEW `src/Medical_KG/ui/briefing/TopicWizard.tsx`
- NEW `src/Medical_KG/ui/briefing/EvidenceWorkspace.tsx`
- NEW `src/Medical_KG/ui/briefing/NarrativeEditor.tsx`
- NEW `src/Medical_KG/ui/briefing/EvidenceMap.tsx`
- NEW `src/Medical_KG/ui/briefing/QuestionGenerator.tsx`
- NEW `src/Medical_KG/ui/briefing/TemplateSelector.tsx`
- NEW `src/Medical_KG/api/briefing_ui.py`
- MODIFIED `src/Medical_KG/briefing/service.py` - add synthesis methods
