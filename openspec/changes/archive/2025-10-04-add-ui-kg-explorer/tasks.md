# Implementation Tasks

## 1. Graph Visualization

- [ ] 1.1 Integrate force-directed graph library (react-force-graph or vis-network)
- [ ] 1.2 Create `GraphCanvas` component with zoom, pan, and node selection
- [ ] 1.3 Implement node styling by label type (Study=blue, Drug=green, Condition=red, etc.)
- [ ] 1.4 Add edge styling by relationship type with directional arrows
- [ ] 1.5 Implement layout algorithms (force, hierarchical, circular) with toggle

## 2. Entity Search & Selection

- [ ] 2.1 Create entity search bar with type-ahead using Cypher MATCH
- [ ] 2.2 Add entity type filter dropdown (Study, Drug, Condition, Outcome, Evidence)
- [ ] 2.3 Implement "Load Entity" button adding node to canvas
- [ ] 2.4 Create recent entities sidebar showing last 20 viewed
- [ ] 2.5 Add "Random Walk" feature loading random connected subgraph

## 3. Entity Detail Panel

- [ ] 3.1 Build `EntityPanel` sidebar showing all node properties
- [ ] 3.2 Display property list with type formatting (dates, numbers, arrays)
- [ ] 3.3 Show incoming and outgoing relationships with counts
- [ ] 3.4 Add provenance section showing source documents and extraction timestamps
- [ ] 3.5 Implement "Edit Properties" mode with validation

## 4. Neighborhood Expansion

- [ ] 4.1 Add "Expand" button on nodes with hop count selector (1, 2, 3)
- [ ] 4.2 Implement progressive loading animation for new nodes
- [ ] 4.3 Create relationship filtering during expansion (include/exclude types)
- [ ] 4.4 Add "Collapse" feature removing expanded subgraph
- [ ] 4.5 Implement path highlighting between two selected nodes

## 5. Visual Query Builder

- [ ] 5.1 Create `QueryBuilder` component with drag-and-drop interface
- [ ] 5.2 Add node pattern blocks (match by label, property constraints)
- [ ] 5.3 Implement relationship pattern connectors (type, direction, property filters)
- [ ] 5.4 Generate Cypher query from visual pattern and display in code editor
- [ ] 5.5 Add "Run Query" button executing Cypher and visualizing results

## 6. Relationship Controls

- [ ] 6.1 Create relationship type legend with show/hide checkboxes
- [ ] 6.2 Add relationship strength slider filtering by edge weight
- [ ] 6.3 Implement edge bundling toggle for dense graphs
- [ ] 6.4 Add directional filtering (incoming only, outgoing only, bidirectional)

## 7. Export & Statistics

- [ ] 7.1 Build export modal with format selection (JSON, GraphML, Cypher, PNG, SVG)
- [ ] 7.2 Implement subgraph selection for partial export
- [ ] 7.3 Create statistics dashboard showing node/edge counts by type
- [ ] 7.4 Add centrality metrics visualization (degree, betweenness, pagerank)
- [ ] 7.5 Implement clustering visualization with community detection

## 8. Backend API

- [ ] 8.1 Add `/api/kg/search` endpoint for entity search with fuzzy matching
- [ ] 8.2 Implement `/api/kg/entity/{id}` GET endpoint returning full entity properties
- [ ] 8.3 Create `/api/kg/neighbors` POST endpoint for neighborhood expansion
- [ ] 8.4 Add `/api/kg/query` POST endpoint executing arbitrary Cypher with safety limits
- [ ] 8.5 Implement `/api/kg/stats` GET endpoint returning graph statistics
- [ ] 8.6 Create `/api/kg/export` POST endpoint generating subgraph exports

## 9. Testing & Documentation

- [ ] 9.1 Write unit tests for KG components (80%+ coverage)
- [ ] 9.2 Add integration tests for graph query API
- [ ] 9.3 Create E2E tests for entity search → expand → export workflow
- [ ] 9.4 Document KG explorer in `docs/ui_kg_explorer.md` with Cypher examples
