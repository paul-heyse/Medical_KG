# Secrets Management

Configuration files never contain raw secrets. Fields such as `api_key`, `jwt_secret`, and `password` use `${VAR_NAME}` placeholders.

## Resolution Order

1. Environment variables passed to the process.
2. Values returned by the injected `SecretResolver` (Vault/KMS adapter).
3. Optional default specified as `${VAR_NAME:default}`.

If a required secret cannot be resolved the loader raises `Missing required secret: <NAME>` and the service fails fast.

## Usage Patterns

- **Environment variables**: export secrets before running the service (`export API_JWT_SECRET=...`).
- **Vault/KMS**: extend `SecretResolver` to call your secret store and pass it to `ConfigManager(secret_resolver=...)`.
- **Overrides**: use `config-override.yaml` for local development with dummy credentials and avoid committing the file.

## Masking

Commands that display configuration (`med config show`) mask keys ending in `_key`, `_secret`, `_token`, or `password`. Placeholder strings that still contain `${...}` are also masked.

## Logging

Never log resolved secrets. The loader masks sensitive values when serialising configurations for debugging.
