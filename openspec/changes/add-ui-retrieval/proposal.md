# Change Proposal: Retrieval & Search UI

## Why

Medical_KG provides sophisticated multi-stage retrieval (BM25, SPLADE, Dense, RRF fusion, reranking) with intent-aware routing, but currently requires API calls. Users need an intuitive search interface with faceted navigation, result previewing, citation export, and query refinement without learning the API schema.

## What Changes

- Create Google-like search interface with autocomplete, query suggestions, and advanced filters
- Build intent-aware search with automatic PICO/effects/AE/dose detection and facet highlighting
- Implement result cards showing chunk text, metadata, retrieval scores, and provenance
- Add result actions: expand context, view in document, add to briefing, export citation
- Provide query refinement UI with synonym expansion, filter adjustments, and reranking toggle
- Create saved searches and search history with collaborative sharing
- Add faceted navigation sidebar (source type, date range, evidence level, population, intervention)
- Implement visual explain mode showing BM25/SPLADE/Dense scores and fusion logic

## Impact

**Affected specs:** NEW `ui-retrieval` capability

**Affected code:**

- NEW `src/Medical_KG/ui/retrieval/SearchBar.tsx` - main search input with autocomplete
- NEW `src/Medical_KG/ui/retrieval/ResultList.tsx` - search results display
- NEW `src/Medical_KG/ui/retrieval/FacetSidebar.tsx` - filtering controls
- NEW `src/Medical_KG/ui/retrieval/ResultCard.tsx` - individual result component
- NEW `src/Medical_KG/ui/retrieval/QueryRefiner.tsx` - query modification UI
- NEW `src/Medical_KG/api/search_ui.py` - search API endpoints with autocomplete
- MODIFIED `src/Medical_KG/retrieval/service.py` - add explain mode flag
