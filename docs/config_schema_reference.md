# Configuration Schema Reference

Generated from `config.schema.json` version `1.0.0`.

This file is generated via `scripts/generate_config_docs.py`. Do not edit manually.

## `$schema`

- **Type**: string
- **Required**: no
- **Format**: uri-reference
- **Description**: JSON Schema reference with embedded version information

## `apis`

- **Type**: any
- **Required**: yes

## `catalog`

- **Type**: any
- **Required**: yes

## `chunking`

- **Type**: object
- **Required**: yes

### `chunking.profiles`

- **Type**: object
- **Required**: yes

## `config_version`

- **Type**: string
- **Required**: yes
- **Description**: Semantic identifier for the configuration payload

## `embeddings`

- **Type**: any
- **Required**: yes

## `entity_linking`

- **Type**: any
- **Required**: yes

## `extraction`

- **Type**: any
- **Required**: yes

## `feature_flags`

- **Type**: any
- **Required**: yes

## `kg`

- **Type**: any
- **Required**: yes

## `licensing`

- **Type**: any
- **Required**: yes

## `observability`

- **Type**: any
- **Required**: yes

## `pipelines`

- **Type**: any
- **Required**: yes

## `retrieval`

- **Type**: any
- **Required**: yes

## `sources`

- **Type**: object
- **Required**: yes
- **Description**: Upstream data sources and credentials
