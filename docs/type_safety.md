# Type Safety Guidelines

This repository adopts strict type checking as part of the "type-safety" capability. All
first-party modules must pass `mypy --strict` and optional dependencies are accessed
through typed facades that keep `Any` from leaking into the codebase.

## Required Workflow

1. **Annotate new code** – functions, methods, and module-level constants MUST be
   annotated. Prefer concrete collection types (`list[str]`) over abstract `Any`.
2. **Use typed facades for optionals** – when working with `httpx`, `locust`, `spaCy`,
   `torch`, or `tiktoken`, import from `Medical_KG.compat` to obtain Protocol-based
   wrappers. These helpers degrade gracefully when the dependency is absent while
   preserving accurate type information for mypy.
3. **Avoid suppressions** – do not introduce `# type: ignore` comments or loosen the
   mypy configuration. Instead, define Protocols, TypedDicts, or helper functions to
   model the behaviour precisely.
4. **Run mypy locally** – execute `mypy --strict src/Medical_KG` (and targeted
   directories under `tests/`) before opening a pull request. CI rejects changes that
   reintroduce type violations.

## Patterns & Examples

### Optional HTTP Clients

```python
from Medical_KG.compat import AsyncClientProtocol, create_async_client

client: AsyncClientProtocol = create_async_client(timeout=5.0)
response = await client.request("GET", "https://example.com")
response.raise_for_status()
```

### spaCy Pipelines

```python
from Medical_KG.compat import load_pipeline

nlp = load_pipeline("en_core_sci_sm")
if nlp is None:
    return []
return [ent.text for ent in nlp(text).ents]
```

### Typed Tokenisation

```python
from Medical_KG.compat import load_encoding

encoding = load_encoding("cl100k_base")
if encoding is None:
    return len(text.split())
return len(encoding.encode(text))
```

## Test Fixtures

- Provide annotations for fixtures and monkeypatch helpers in `conftest.py`.
- Prefer Protocol-based mocks so mypy can enforce call signatures.
- Avoid manipulating `sys.path`; use `importlib` and typed factories instead.

## Enforcement

- `pyproject.toml` configures `mypy` in strict mode.
- CI runs `mypy --strict` and `pytest` for every PR.
- Any attempt to add suppressions or relax strictness will fail the build.

For quick reference, keep the compatibility helpers in mind and consult this document
when introducing new optional dependencies or asynchronous adapters.
