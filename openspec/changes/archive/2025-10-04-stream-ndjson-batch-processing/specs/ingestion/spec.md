# Ingestion Batch Processing Performance

## MODIFIED Requirements

### Requirement: Memory-Efficient Batch Processing

The ingestion CLI SHALL process NDJSON batch files with constant memory usage regardless of file size, enabling large-scale re-ingestion campaigns.

#### Scenario: Large batch file processing

- **WHEN** a batch file contains 1 million records
- **THEN** the CLI SHALL stream records incrementally
- **AND** SHALL NOT load the entire file into memory
- **AND** SHALL maintain constant O(1) memory usage
- **AND** SHALL NOT cause Out-Of-Memory errors

#### Scenario: Incremental progress reporting

- **WHEN** processing a large batch file
- **THEN** the CLI SHALL report progress incrementally (per record or per chunk)
- **AND** SHALL NOT wait until batch completion to show feedback
- **AND** SHALL display current record count, total, and ETA

#### Scenario: Streaming pipeline results

- **WHEN** an ingestion pipeline processes multiple adapters
- **THEN** the pipeline SHALL yield documents as they are produced
- **AND** SHALL NOT materialize all results in memory before returning
- **AND** SHALL enable streaming telemetry and incremental processing

## ADDED Requirements

### Requirement: Pipeline Streaming Iterator

The ingestion pipeline SHALL provide an async iterator interface for streaming document results, enabling incremental processing and lower memory usage.

#### Scenario: Streaming document iteration

- **WHEN** a caller uses `IngestionPipeline.iter_results()`
- **THEN** the pipeline SHALL yield Document objects incrementally
- **AND** SHALL NOT wait for all adapters to complete
- **AND** SHALL enable processing documents as they arrive

#### Scenario: Backward compatibility maintained

- **WHEN** existing code calls `IngestionPipeline.run_async()`
- **THEN** the method SHALL continue to work without changes
- **AND** SHALL internally use streaming implementation
- **AND** SHALL return list of results as before
