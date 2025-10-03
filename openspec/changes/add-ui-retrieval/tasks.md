# Implementation Tasks

## 1. Search Interface

- [ ] 1.1 Create `SearchBar` component with autocomplete dropdown
- [ ] 1.2 Implement query suggestion API using recent searches and entity catalog
- [ ] 1.3 Add advanced search modal with field-specific inputs (title, abstract, author, etc.)
- [ ] 1.4 Create search history dropdown showing last 20 queries
- [ ] 1.5 Add voice search input using Web Speech API

## 2. Results Display

- [ ] 2.1 Build `ResultList` component with virtualized scrolling for 1000+ results
- [ ] 2.2 Create `ResultCard` showing chunk text, scores, metadata, and actions
- [ ] 2.3 Add snippet highlighting for query terms with context window
- [ ] 2.4 Implement result sorting (relevance, date, source credibility)
- [ ] 2.5 Add pagination vs. infinite scroll toggle

## 3. Faceted Navigation

- [ ] 3.1 Create `FacetSidebar` with collapsible facet groups
- [ ] 3.2 Add facet types: source, date range, study type, evidence level, population age/gender
- [ ] 3.3 Implement multi-select facets with "AND"/"OR" logic toggle
- [ ] 3.4 Display facet counts and update dynamically with query changes
- [ ] 3.5 Add "Clear All Filters" and individual facet removal chips

## 4. Intent Detection & Highlighting

- [ ] 4.1 Display detected intent badge (PICO/Effects/AE/Dose/Eligibility) above results
- [ ] 4.2 Highlight facet-relevant spans in result snippets (e.g., hazard ratios for Effects intent)
- [ ] 4.3 Add intent override dropdown to manually switch intent
- [ ] 4.4 Show expanded ontology terms used in query

## 5. Result Actions

- [ ] 5.1 Add "Expand Context" button loading ±2 neighboring chunks
- [ ] 5.2 Create "View in Document" link navigating to document viewer with scroll-to-chunk
- [ ] 5.3 Implement "Add to Briefing" action opening briefing selector
- [ ] 5.4 Build "Export Citation" modal with BibTeX, RIS, AMA, Vancouver formats
- [ ] 5.5 Add "Similar Results" link running query expansion from selected chunk

## 6. Query Refinement

- [ ] 6.1 Create `QueryRefiner` panel showing query analysis breakdown
- [ ] 6.2 Display synonym expansions as removable chips with boost values
- [ ] 6.3 Add reranking toggle with model selection dropdown
- [ ] 6.4 Implement "Explain Scores" mode showing BM25/SPLADE/Dense/RRF breakdown per result
- [ ] 6.5 Create query suggestion chips based on partial matches

## 7. Saved Searches

- [ ] 7.1 Add "Save Search" button storing query + filters with name and description
- [ ] 7.2 Create saved searches sidebar listing user's saved searches
- [ ] 7.3 Implement search alerts (email when new matching documents ingested)
- [ ] 7.4 Add collaborative sharing of saved searches via shareable links

## 8. Backend API

- [ ] 8.1 Add `/api/retrieval/autocomplete` endpoint for query suggestions
- [ ] 8.2 Extend `/retrieve` endpoint with `explain=true` flag returning score breakdowns
- [ ] 8.3 Create `/api/retrieval/similar` endpoint for semantic similarity search
- [ ] 8.4 Add `/api/retrieval/saved-searches` CRUD endpoints
- [ ] 8.5 Implement `/api/retrieval/history` storing user search history

## 9. Testing & Documentation

- [ ] 9.1 Write unit tests for retrieval components (80%+ coverage)
- [ ] 9.2 Add integration tests for search API with various intents
- [ ] 9.3 Create E2E tests for search → filter → refine → export workflow
- [ ] 9.4 Document search UI in `docs/ui_retrieval.md` with query examples
