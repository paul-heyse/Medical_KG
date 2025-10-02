# Configuration Management Capability

## ADDED Requirements

### Requirement: Master config.yaml Structure

The system SHALL define comprehensive config.yaml with sections for sources, chunking, embeddings, retrieval, extraction, kg, catalog, apis, observability, and licensing.

#### Scenario: Sources configuration

- **WHEN** configuring data sources
- **THEN** config.yaml SHALL include sources{ncbi, openfda, dailymed} with {api_key?, rate_limit, retry_config}

#### Scenario: Chunking profiles

- **WHEN** configuring chunking
- **THEN** config.yaml SHALL include chunking.profiles{imrad, registry, spl, guideline} with {target_tokens, overlap, tau_coh}

#### Scenario: Retrieval fusion weights

- **WHEN** configuring retrieval
- **THEN** config.yaml SHALL include retrieval.fusion.weights{bm25, splade, dense} that sum to 1.0±0.01

### Requirement: JSON Schema Validation

The system SHALL validate config.yaml against config.schema.json on startup and before hot-reload.

#### Scenario: Schema validation on startup

- **WHEN** service initializes
- **THEN** the system SHALL load config.yaml, validate against config.schema.json, and fail-fast if invalid

#### Scenario: Constraint validation

- **WHEN** validating config
- **THEN** the system SHALL verify: retrieval fusion weights sum=1.0, chunking target_tokens >0, rate_limits >0

#### Scenario: Enum validation

- **WHEN** checking config fields
- **THEN** the system SHALL validate enums (log_level: debug|info|warn|error, intent: pico|endpoint|ae|dose|eligibility|general)

### Requirement: Hierarchical Overrides

The system SHALL support config overrides via config-override.yaml and environment variables.

#### Scenario: Load base config

- **WHEN** service starts
- **THEN** the system SHALL load config.yaml as base configuration

#### Scenario: Apply override file

- **WHEN** config-override.yaml exists
- **THEN** the system SHALL overlay overrides on base config (deep merge)

#### Scenario: Apply environment variables

- **WHEN** environment variables like VLLM_API_BASE set
- **THEN** the system SHALL overlay env vars on top of file configs (highest precedence)

### Requirement: Hot-Reload Support

The system SHALL support hot-reload of non-breaking config changes via POST /admin/reload.

#### Scenario: Reload endpoint

- **WHEN** POST /admin/reload with admin scope + signed JWT
- **THEN** the system SHALL re-read configs, validate, and apply non-breaking changes without restart

#### Scenario: Apply non-breaking changes

- **WHEN** reloading config
- **THEN** the system SHALL apply: retrieval weights, log level, rate limits, feature flags

#### Scenario: Reject breaking changes

- **WHEN** config change affects vllm_api_base or neo4j_uri
- **THEN** the system SHALL reject reload with error "Breaking change requires restart"

#### Scenario: Increment config version

- **WHEN** hot-reload succeeds
- **THEN** the system SHALL increment config_version and emit metric

### Requirement: Feature Flags

The system SHALL support feature flags for toggling experimental features.

#### Scenario: Define feature flags

- **WHEN** configuring features
- **THEN** config.yaml SHALL include feature_flags{splade_enabled, reranker_enabled, extraction_experimental_enabled}

#### Scenario: Check flags at runtime

- **WHEN** SPLADE retriever is invoked and splade_enabled=false
- **THEN** the system SHALL skip SPLADE and adjust fusion weights (redistribute to bm25/dense)

#### Scenario: Emit flag states

- **WHEN** monitoring features
- **THEN** the system SHALL emit metrics feature_flag{name, enabled}

### Requirement: Licensing Configuration

The system SHALL load licensing config from policy.yaml with vocabulary gates.

#### Scenario: Load policy.yaml

- **WHEN** service starts
- **THEN** the system SHALL load policy.yaml with vocabs{SNOMED{licensed, territory}, MedDRA{licensed}, LOINC{licensed}}

#### Scenario: Refuse unlicensed loading

- **WHEN** SNOMED loader invoked and LIC_SNOMED=false
- **THEN** the system SHALL exit with error "SNOMED requires affiliate license"

#### Scenario: Filter by license tier

- **WHEN** API request includes X-License-Tier=public
- **THEN** the system SHALL filter results per policy.yaml vocabulary gates

### Requirement: Config Versioning

The system SHALL track config version with SHA256 hash for change detection.

#### Scenario: Compute config hash

- **WHEN** loading config
- **THEN** the system SHALL compute SHA256 of canonical YAML (sorted keys)

#### Scenario: Store config version

- **WHEN** config loaded
- **THEN** the system SHALL set config_version={semantic_version or timestamp, hash}

#### Scenario: Emit config version metric

- **WHEN** service running
- **THEN** the system SHALL emit config_info{version, hash} metric

### Requirement: Environment-Specific Configs

The system SHALL support config-dev.yaml, config-staging.yaml, config-prod.yaml selected by CONFIG_ENV.

#### Scenario: Dev config

- **WHEN** CONFIG_ENV=dev
- **THEN** the system SHALL load config-dev.yaml (mock APIs, verbose logging)

#### Scenario: Staging config

- **WHEN** CONFIG_ENV=staging
- **THEN** the system SHALL load config-staging.yaml (real APIs with test keys)

#### Scenario: Prod config

- **WHEN** CONFIG_ENV=prod
- **THEN** the system SHALL load config-prod.yaml (secrets from Vault, strict licensing)

### Requirement: Secrets Management

The system SHALL resolve secret placeholders from Vault/KMS at runtime.

#### Scenario: Placeholder resolution

- **WHEN** config contains ${UMLS_API_KEY}
- **THEN** the system SHALL resolve from Vault or environment variable

#### Scenario: Mask secrets in logs

- **WHEN** logging config
- **THEN** the system SHALL mask all fields matching *_KEY,*_SECRET, *_TOKEN patterns

#### Scenario: Fail on missing secrets

- **WHEN** required secret unresolved
- **THEN** the system SHALL fail startup with error "Missing required secret: UMLS_API_KEY"

### Requirement: CLI Validation

The system SHALL provide `med config validate --strict` for offline validation.

#### Scenario: Validate config

- **WHEN** running `med config validate --strict`
- **THEN** the system SHALL load config, validate schema, check constraints, and report all errors/warnings

#### Scenario: Exit code

- **WHEN** validation fails
- **THEN** the system SHALL exit with code 1 and list all violations

#### Scenario: Success output

- **WHEN** validation passes
- **THEN** the system SHALL print "Config valid" and exit with code 0
