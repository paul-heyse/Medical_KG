# Change Proposal: Knowledge Graph Explorer UI

## Why

Medical_KG stores structured clinical knowledge in a Neo4j graph (Studies, Drugs, Conditions, Outcomes, Evidence) with complex relationships. Users need a visual graph explorer to navigate entity relationships, discover connections, validate data quality, and export subgraphs without writing Cypher queries.

## What Changes

- Create interactive graph visualization using force-directed layout with zoom/pan/filter
- Build entity detail panels showing all properties, relationships, and provenance
- Implement graph query builder with visual relationship path construction
- Add neighborhood exploration (1-hop, 2-hop, 3-hop expansion)
- Provide entity search with type-ahead and filtering by node label
- Create relationship filtering (show/hide relationship types, relationship strength thresholds)
- Add export functionality (subgraph as JSON/GraphML/Cypher, entity report as PDF)
- Implement graph statistics dashboard (node/edge counts by type, centrality metrics, clustering coefficient)
- Provide diff view for comparing graph state between ingestion batches

## Impact

**Affected specs:** NEW `ui-kg-explorer` capability

**Affected code:**

- NEW `src/Medical_KG/ui/kg/GraphCanvas.tsx` - force-directed graph visualization
- NEW `src/Medical_KG/ui/kg/EntityPanel.tsx` - entity detail sidebar
- NEW `src/Medical_KG/ui/kg/QueryBuilder.tsx` - visual Cypher builder
- NEW `src/Medical_KG/ui/kg/RelationshipFilter.tsx` - relationship controls
- NEW `src/Medical_KG/api/kg_explorer.py` - graph query APIs
- MODIFIED `src/Medical_KG/kg/service.py` - add neighborhood query methods
