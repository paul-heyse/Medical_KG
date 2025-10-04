# Optional dependency matrix

Medical KG ships a slim core install and activates additional capabilities when
optional extras are available. The sections below describe each extras group,
its packages, and the features unlocked once installed.

Use `med dependencies check` to view the status of every group locally:

```bash
$ med dependencies check
observability [observability]: installed
pdf_processing [pdf]: missing
  missing: pypdf, pdfminer.six
  install: pip install medical-kg[pdf]
```

Pass `--json` for machine-readable output or `--verbose` to include package
lists, install hints, and documentation links.

## Observability

- **Extras group**: `observability`
- **Features**: Prometheus metrics, OpenTelemetry tracing, OTLP exporter
- **Packages**:
  - `prometheus-client==0.23.1`
  - `python-json-logger==3.3.0`
  - `opentelemetry-api==1.37.0`
  - `opentelemetry-sdk==1.37.0`
  - `opentelemetry-instrumentation-fastapi==0.58b0`
  - `opentelemetry-instrumentation-httpx==0.58b0`
  - `opentelemetry-exporter-otlp==1.37.0`
- **Install**: `pip install medical-kg[observability]`

## PDF processing

- **Extras group**: `pdf`
- **Features**: MinerU ingestion, PDF parsing utilities
- **Packages**:
  - `pypdf==6.1.1`
  - `pdfminer.six==20250506`
  - `pypdfium2==4.30.0`
- **Install**: `pip install medical-kg[pdf]`

## Embeddings

- **Extras group**: `embeddings`
- **Features**: Dense + sparse embedding pipelines
- **Packages**:
  - `sentence-transformers==5.1.1`
  - `sentencepiece==0.2.1`
  - `faiss-cpu>=1.7.4`
- **Install**: `pip install medical-kg[embeddings]`

## Tokenization

- **Extras group**: `tokenization`
- **Features**: Tiktoken-backed token counting
- **Packages**: `tiktoken==0.11.0`
- **Install**: `pip install medical-kg[tokenization]`

## Natural language processing

- **Extras group**: `nlp`
- **Features**: spaCy NER pipelines used by extraction flows
- **Packages**: `spacy==3.7.5`
- **Install**: `pip install medical-kg[nlp]`
- **Note**: Domain-specific models (e.g. `en_core_sci_md`) must be downloaded
  separately via `python -m spacy download ...`.

## GPU

- **Extras group**: `gpu`
- **Features**: Torch-backed GPU helpers for embeddings and vLLM
- **Packages**: `torch`
- **Install**: `pip install medical-kg[gpu]`
- **Note**: Install the CUDA build that matches your environment (e.g. via the
  PyTorch install selector).

## HTTP clients

- **Extras group**: `http`
- **Features**: `httpx` powered ingestion, API clients, and telemetry hooks
- **Packages**: `httpx==0.28.1`
- **Install**: `pip install medical-kg[http]`

## Caching

- **Extras group**: `caching`
- **Features**: Redis-backed cache and rate-limit stores
- **Packages**: `redis==6.4.0`
- **Install**: `pip install medical-kg[caching]`

## Load testing

- **Extras group**: `load-testing`
- **Features**: Locust-based ingestion load tests
- **Packages**: `locust>=2.24.1`
- **Install**: `pip install medical-kg[load-testing]`

## Checking installed groups

Run `med dependencies check` to list all groups. Missing dependencies return an
exit code of `1`, making the command suitable for CI smoke-tests:

```bash
$ med dependencies check --json > dependencies.json
```

Use `--verbose` to include install hints and documentation links, or inspect
specific fields with `jq` in pipelines.

## Adding a new optional dependency

1. Add or update the extras group in `pyproject.toml`.
2. Extend `DEPENDENCY_REGISTRY` in `Medical_KG.utils.optional_dependencies` with
   the feature name, packages, extras group, and documentation link.
3. Provide a type stub (either via `types-...` packages or a `.pyi` file under
   `stubs/`) so `mypy --strict` continues to pass without the dependency.
4. Update this document with the new group and feature description.
5. Add or adjust tests that exercise the new optional import path.

## Troubleshooting

- Missing packages raise `MissingDependencyError` with a clear install hint and
  documentation link. Re-run `med dependencies check` after installing extras.
- If the CLI reports a package as missing even after installation, ensure your
  virtual environment matches the interpreter used by `med` and re-run
  `pip install --upgrade pip` before reinstalling the extras group.
- When adding new stubs, run `mypy --strict` locally to confirm the override
  list does not need additional entries.
