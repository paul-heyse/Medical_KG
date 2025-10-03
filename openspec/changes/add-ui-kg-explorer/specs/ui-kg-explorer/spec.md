# UI Knowledge Graph Explorer Specification

## Overview

The KG Explorer provides interactive visualization and querying of the Medical_KG Neo4j graph with entity relationships, provenance tracking, and subgraph export.

## ADDED Requirements

### Requirement: Interactive Graph Visualization

The UI SHALL render the knowledge graph using force-directed layout with zoom, pan, node selection, and relationship filtering.

#### Scenario: Initial graph load

- **WHEN** a user searches for an entity and clicks "Load in Graph"
- **THEN** the graph canvas SHALL render centered on that entity node
- **AND** immediate neighbors (1-hop) SHALL load automatically
- **AND** nodes SHALL be color-coded by label type (Study=blue, Drug=green, Condition=red, Outcome=purple)
- **AND** edges SHALL show directional arrows with relationship type labels

#### Scenario: Graph interactions

- **WHEN** a user interacts with the graph
- **THEN** scroll wheel SHALL zoom in/out smoothly
- **AND** click-drag on canvas SHALL pan the view
- **AND** clicking a node SHALL select it and highlight connected edges
- **AND** double-clicking a node SHALL expand its neighbors

### Requirement: Entity Detail Panel

Selecting a node SHALL open a detail panel showing all properties, relationships, and provenance metadata.

#### Scenario: Entity properties display

- **WHEN** a user clicks a Study node
- **THEN** the detail panel SHALL show: node ID, label, NCT ID, title, phase, status, enrollment, sponsor, dates
- **AND** properties SHALL be formatted by type (dates as YYYY-MM-DD, numbers with commas)
- **AND** array properties SHALL display as bulleted lists

#### Scenario: Relationship listing

- **WHEN** the detail panel is open
- **THEN** a "Relationships" section SHALL list incoming and outgoing edges grouped by type
- **AND** each relationship SHALL show: type, target node label, target node name, relationship properties
- **AND** clicking a relationship SHALL navigate to the target node

#### Scenario: Provenance display

- **WHEN** viewing entity details
- **THEN** a "Provenance" section SHALL show: source documents, extraction timestamps, confidence scores, ingestion batch ID
- **AND** clicking a source document SHALL navigate to document viewer

### Requirement: Neighborhood Expansion

Users SHALL be able to progressively expand node neighborhoods to specified hop depths with relationship filtering.

#### Scenario: 1-hop expansion

- **WHEN** a user clicks "Expand" on a selected node with hop=1
- **THEN** all immediate neighbors SHALL load with animation
- **AND** new nodes SHALL fade in over 300ms
- **AND** new edges SHALL draw from center node to neighbors

#### Scenario: Filtered expansion

- **WHEN** a user expands a node with relationship type filters active
- **THEN** only relationships of selected types SHALL be followed
- **AND** excluded relationship types SHALL remain hidden
- **AND** the expansion indicator SHALL show "X of Y relationships shown"

#### Scenario: Path highlighting

- **WHEN** a user selects two nodes
- **THEN** shortest paths between them SHALL highlight in gold
- **AND** a path sidebar SHALL list all paths with hop counts
- **AND** clicking a path SHALL focus the graph on that path

### Requirement: Visual Query Builder

The UI SHALL provide a drag-and-drop interface for constructing Cypher queries visually without syntax knowledge.

#### Scenario: Query pattern construction

- **WHEN** a user opens the query builder
- **THEN** a canvas SHALL display for arranging node and relationship patterns
- **AND** a palette SHALL provide draggable blocks (Match Node, Match Relationship, Where Clause, Return)
- **AND** connecting blocks with arrows SHALL define relationship patterns

#### Scenario: Cypher generation

- **WHEN** a user completes a visual query
- **THEN** the generated Cypher SHALL display in a syntax-highlighted editor
- **AND** users SHALL be able to manually edit the Cypher
- **AND** clicking "Run Query" SHALL execute against Neo4j and render results in graph

#### Scenario: Query validation

- **WHEN** a user builds an invalid query pattern
- **THEN** validation errors SHALL highlight problematic blocks in red
- **AND** error messages SHALL explain the issue (e.g., "Relationship must connect two nodes")

### Requirement: Subgraph Export

Users SHALL be able to select subgraphs and export in multiple formats (JSON, GraphML, Cypher, SVG).

#### Scenario: Subgraph selection

- **WHEN** a user enables "Select Mode"
- **THEN** clicking nodes SHALL toggle their selection (blue outline)
- **AND** a selection count SHALL display "X nodes, Y edges selected"
- **AND** "Select Connected" button SHALL extend selection to all connected nodes

#### Scenario: Export format selection

- **WHEN** a user clicks "Export" with nodes selected
- **THEN** a modal SHALL offer format choices (JSON, GraphML, Cypher CREATE statements, PNG, SVG)
- **AND** selecting JSON SHALL download a file with nodes and edges arrays
- **AND** selecting SVG SHALL export the current graph view as vector graphic

### Requirement: Graph Statistics Dashboard

The UI SHALL provide aggregate statistics on node and edge counts, centrality metrics, and community clustering.

#### Scenario: Statistics overview

- **WHEN** a user opens the statistics panel
- **THEN** cards SHALL display: total node count by label, total edge count by type, average degree, clustering coefficient
- **AND** a bar chart SHALL show node distribution by label
- **AND** a timeline SHALL show graph growth over time (if historical data available)

#### Scenario: Centrality metrics

- **WHEN** a user requests centrality analysis
- **THEN** top 10 nodes by degree centrality SHALL display
- **AND** users SHALL be able to switch metrics (degree, betweenness, pagerank, closeness)
- **AND** clicking a high-centrality node SHALL load it in the graph canvas

### Requirement: Real-Time Collaboration

Multiple users SHALL be able to explore the graph simultaneously with shared cursor positions and annotations.

#### Scenario: User presence

- **WHEN** multiple users view the same graph
- **THEN** each user's cursor SHALL display as a colored dot with name label
- **AND** when a user selects a node, it SHALL highlight for all viewers
- **AND** users SHALL be able to drop annotation pins with text comments

### Requirement: Performance for Large Graphs

The graph visualization SHALL handle 1000+ nodes efficiently with pagination, clustering, and lazy loading.

#### Scenario: Node limit warning

- **WHEN** a query would return more than 1000 nodes
- **THEN** a warning modal SHALL appear "Large result set detected (X nodes). Load anyway or refine query?"
- **AND** choosing "Refine" SHALL suggest filtering by relationship type or depth limit

#### Scenario: Clustering for density

- **WHEN** the graph has high-degree nodes causing visual clutter
- **THEN** users SHALL be able to enable "Cluster Mode" grouping similar nodes
- **AND** clusters SHALL render as larger composite nodes with count badges
- **AND** expanding a cluster SHALL reveal individual nodes
