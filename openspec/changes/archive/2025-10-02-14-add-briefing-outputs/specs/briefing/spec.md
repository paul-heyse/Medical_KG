# Briefing Outputs Capability

## ADDED Requirements

### Requirement: Topic Dossier Generation

The system SHALL generate comprehensive topic dossiers with PICO synopsis, endpoints, safety, dosing, eligibility, and guidelines, all with 100% citation coverage.

#### Scenario: Query KG for topic

- **WHEN** generating dossier for topic={condition: "SNOMED:44054006", intervention: "RxCUI:1234", outcome: "LOINC:4548-4"}
- **THEN** the system SHALL query Neo4j for all studies matching topic filters via (:Study)-[:ABOUT]->(:Concept) paths

#### Scenario: Aggregate PICO

- **WHEN** synthesizing PICO section
- **THEN** the system SHALL collect all :EvidenceVariable nodes, deduplicate populations/interventions/outcomes, and format with citations

#### Scenario: Aggregate endpoints

- **WHEN** synthesizing endpoints section
- **THEN** the system SHALL collect :Evidence nodes, group by outcome, compute meta-analysis or list individual effects with heterogeneity I²

#### Scenario: Aggregate safety

- **WHEN** synthesizing safety section
- **THEN** the system SHALL collect :AdverseEvent nodes, group by MedDRA PT + grade, compute rates per arm, and cite sources

#### Scenario: 100% citation coverage

- **WHEN** any claim is included in dossier
- **THEN** assertion MUST link to spans_json with doc_id + offsets or be omitted

### Requirement: Evidence Map Builder

The system SHALL create evidence maps showing who found what in which population with certainty ratings.

#### Scenario: Query all evidence

- **WHEN** building evidence map
- **THEN** the system SHALL MATCH (:Evidence)-[:MEASURES]->(:Outcome), (:Evidence)<-[:REPORTS]-(:Study) and extract {study_id, population, intervention, outcome, effect, certainty, citation}

#### Scenario: Group by dimensions

- **WHEN** organizing map
- **THEN** the system SHALL group evidence by outcome → intervention → population hierarchy

#### Scenario: Detect conflicts

- **WHEN** same outcome+intervention has contradictory effects (HR <1 vs HR >1 with non-overlapping CIs)
- **THEN** the system SHALL flag as conflict and include heterogeneity note

#### Scenario: Identify gaps

- **WHEN** PICO mentions outcome but no :Evidence exists
- **THEN** the system SHALL list as evidence gap

### Requirement: Interview Kit Generation

The system SHALL generate interview kits with auto-proposed questions on unresolved evidence, subpopulations, and safety.

#### Scenario: Identify gaps

- **WHEN** analyzing topic evidence
- **THEN** the system SHALL detect: outcomes with no evidence, interventions with single study, AEs mentioned but no grade

#### Scenario: Identify conflicts

- **WHEN** heterogeneous effects or contradictory findings detected
- **THEN** the system SHALL flag for further investigation

#### Scenario: Generate question bank

- **WHEN** gaps/conflicts identified
- **THEN** the system SHALL generate questions using template "What is known about {outcome} in {subpopulation}? [1 study, low certainty]"

#### Scenario: Prioritize questions

- **WHEN** ranking questions
- **THEN** the system SHALL prioritize: high-impact gaps first, conflicts second, open questions third

### Requirement: Coverage Report

The system SHALL produce coverage reports listing included studies, evidence counts, and known gaps.

#### Scenario: List studies

- **WHEN** generating coverage report
- **THEN** the system SHALL enumerate all NCT IDs, PMIDs, SPL setids, guideline IDs contributing to dossier

#### Scenario: Count evidence nodes

- **WHEN** reporting coverage
- **THEN** the system SHALL count :EvidenceVariable, :Evidence, :AdverseEvent, :EligibilityConstraint nodes

#### Scenario: Identify data gaps

- **WHEN** analyzing coverage
- **THEN** the system SHALL identify: "No long-term safety >2 years", "No pediatric trials", "No head-to-head vs competitor X"

#### Scenario: Report freshness

- **WHEN** completing coverage report
- **THEN** the system SHALL include most recent study date, guideline version, catalog release date

### Requirement: Synthesis Rules

The system SHALL apply synthesis rules for meta-analysis, conflict detection, certainty prioritization, and subpopulation stratification.

#### Scenario: Meta-analysis

- **WHEN** ≥3 homogeneous studies available
- **THEN** the system SHALL compute pooled effect with random-effects model

#### Scenario: Heterogeneity handling

- **WHEN** I² >50%
- **THEN** the system SHALL list individual effects with heterogeneity note instead of pooling

#### Scenario: Certainty prioritization

- **WHEN** multiple evidence items for same outcome
- **THEN** the system SHALL prefer high/moderate certainty and flag low/very-low certainty

#### Scenario: Subpopulation stratification

- **WHEN** age/sex/race subgroup data available
- **THEN** the system SHALL present evidence separately by subpopulation

### Requirement: Citation Management

The system SHALL format citations in APA/Vancouver style with inline links and bibliography.

#### Scenario: Inline citations

- **WHEN** rendering dossier in Markdown/HTML
- **THEN** the system SHALL format citations as [source_id] with hover tooltip showing quote

#### Scenario: Bibliography section

- **WHEN** completing dossier
- **THEN** the system SHALL list all sources with full metadata (PMID, NCT, DOI, title, year, journal)

#### Scenario: Citation validation

- **WHEN** generating dossier
- **THEN** the system SHALL verify all doc_ids in citations exist and spans are valid

### Requirement: Output Formats

The system SHALL support Markdown, HTML, JSON, PDF, and Word export formats.

#### Scenario: Markdown template

- **WHEN** format="md"
- **THEN** the system SHALL render using sections: Summary, PICO, Endpoints, Safety, Dosing, Eligibility, Guidelines, Coverage, Questions

#### Scenario: HTML template

- **WHEN** format="html"
- **THEN** the system SHALL render styled HTML with collapsible sections and citation tooltips

#### Scenario: JSON export

- **WHEN** format="json"
- **THEN** the system SHALL return machine-readable structure with all fields + citations[]

#### Scenario: PDF export

- **WHEN** format="pdf"
- **THEN** the system SHALL convert Markdown to PDF via pandoc

### Requirement: Real-Time Q&A Mode

The system SHALL answer natural language queries on-the-fly with retrieval, extraction, and synthesis.

#### Scenario: Accept NL query

- **WHEN** POST /briefing/qa with {query: "Does sacubitril/valsartan reduce CV mortality vs enalapril in HFrEF?"}
- **THEN** the system SHALL detect intent=endpoint

#### Scenario: Retrieve relevant chunks

- **WHEN** processing query
- **THEN** the system SHALL run fusion retrieval (BM25/SPLADE/Dense) and return top-20 chunks

#### Scenario: Extract on-the-fly

- **WHEN** relevant chunks retrieved
- **THEN** the system SHALL run effects extractor and synthesize answer

#### Scenario: Return structured answer

- **WHEN** synthesis completes
- **THEN** the system SHALL return {answer, evidence[{text, citation, confidence}], conflicts[], gaps[]}

### Requirement: Quality Checks

The system SHALL validate 100% citation coverage and detect hallucinations.

#### Scenario: Verify citation coverage

- **WHEN** dossier generated
- **THEN** the system SHALL verify every claim has ≥1 span or be rejected

#### Scenario: Validate spans

- **WHEN** checking citations
- **THEN** the system SHALL verify all doc_ids exist and offsets valid within documents

#### Scenario: Hallucination detection

- **WHEN** synthesizing answer
- **THEN** the system SHALL reject claims without supporting spans (no inference allowed)

#### Scenario: Answer utility measurement

- **WHEN** evaluating Q&A outputs
- **THEN** human evaluators SHALL rate 0=unusable, 1=partially useful, 2=directly actionable (target avg ≥1.6)

### Requirement: API Endpoints

The system SHALL provide POST endpoints for all briefing outputs.

#### Scenario: Generate dossier endpoint

- **WHEN** POST /briefing/dossier with {topic, format}
- **THEN** the system SHALL return {dossier, citations[], meta{study_count, evidence_count}}

#### Scenario: Evidence map endpoint

- **WHEN** POST /briefing/evidence-map with {topic}
- **THEN** the system SHALL return {map[], conflicts[], gaps[]}

#### Scenario: Interview kit endpoint

- **WHEN** POST /briefing/interview-kit with {topic}
- **THEN** the system SHALL return {questions[], context[]}

#### Scenario: Coverage endpoint

- **WHEN** POST /briefing/coverage with {topic}
- **THEN** the system SHALL return {studies[], evidence_counts{}, gaps[], freshness{}}
