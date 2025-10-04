# Configuration Schema Authoring Guide

This guide captures the conventions for extending `config.schema.json` now that the configuration runtime is powered by `jsonschema`.

## Draft 7 Dialect

- Always declare `"$schema": "http://json-schema.org/draft-07/schema#"` at the top of the document.
- Keep `"version"` in sync with runtime support (`ConfigSchemaValidator.CURRENT_SCHEMA_VERSION`).
- Update `docs/config_schema_changelog.md` whenever the version increments.

## Structure and Reuse

- Place shared fragments under `definitions` and reference them with `$ref`.
- Keep property definitions alphabetised to minimise diffs.
- Use `additionalProperties: false` by default to catch typos; explicitly opt-in when free-form maps are required.

## Advanced Composition Patterns

- `oneOf` — use when a configuration block should accept mutually exclusive shapes. Example: `fusionConfig` now allows either explicit weights or a named `weights_profile` preset.
- `anyOf` + `if/then/else` — use for conditional requirements. Example: `sourceConfig` enforces `client_secret` whenever `client_id` appears, otherwise it falls back to `api_key`.
- `allOf` — reserve for shared constraints that combine with base types.
- `dependencies` — prefer `if/then/else` for clarity; keep dependencies for simple optional pairings.

Every advanced construct should include a short `description` so schema readers understand the intent.

## Custom Formats

Registered custom formats live in `ConfigSchemaValidator`:

| Format | Description |
| --- | --- |
| `duration` | Strings such as `"5m"`, `"15m"`, `"1h"`.
| `adapter_name` | Must match an adapter registered in the ingestion registry.
| `file_path` | Relative or absolute path that resolves within the config directory.
| `url_with_scheme` | HTTP/S URLs only.
| `log_level` | Standard logging levels, case-insensitive.

Prefer formats over regexes so validation errors are meaningful and the logic is shared with other tools.

## Authoring Process

1. Update `config.schema.json` with the new fields and constraints.
2. Validate the schema: `med config validate-schema --config-dir src/Medical_KG/config`.
3. Document the change in `docs/configuration.md` and `docs/config_schema_changelog.md`.
4. Add or update unit tests in `tests/config/test_schema_validator.py`.
5. Run the validation CLI against all environment configs: `python scripts/validate_all_configs.py`.

## Error Messaging

The runtime formats validation failures with JSON Pointers, expected values, and remediation hints. When introducing new constraints, add domain-specific hints in `_remediation_hint` so operators know how to fix issues quickly.

## IDE Integration

Modern editors speak JSON Schema directly, so wire them into `config.schema.json` for fast feedback:

- **VS Code** – add to your workspace settings:

  ```json
  {
    "yaml.schemas": {
      "./src/Medical_KG/config/config.schema.json": [
        "src/Medical_KG/config/config.yaml",
        "src/Medical_KG/config/config-*.yaml"
      ]
    }
  }
  ```

- **JetBrains IDEs** – open *Settings → Languages & Frameworks → Schemas and DTDs → JSON Schema*, add the schema file, and map it to the same glob patterns.
- **Neovim / coc-yaml** – declare the schema in your `coc-settings.json` under `yaml.schemas` exactly as above.

Checking the schema into source control means each engineer receives identical validation without configuring remote URLs.

## Schema-driven editor features

Once the schema is associated, editors light up with:

- **Autocomplete** for property names, enum values, and boolean literals.
- **Inline documentation** rendered from each property's `description` – keep them crisp and action oriented.
- **Real-time diagnostics** that match `ConfigSchemaValidator` (including custom formats), so issues are caught before committing.

When adding new schema fragments, take a moment to populate `description`, `enum`, and `default` metadata – doing so directly improves the IDE experience for everyone.
