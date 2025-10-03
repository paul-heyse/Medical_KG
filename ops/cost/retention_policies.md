# Data Retention & TTL Policies

| System              | Policy                                   | Rationale                                   |
|---------------------|------------------------------------------|---------------------------------------------|
| Kafka (ingest)      | 14 days (`log.retention.hours=336`)      | Replay recent ingestion while limiting disk |
| Object storage      | 30 days for raw documents, lifecycle to Glacier after 90 days | Reduce S3 cost, retain for audits          |
| OpenSearch logs     | 7 days hot → 30 days warm → delete       | Fast search for recent ops, archive old data|
| Neo4j snapshots     | Daily snapshots kept 14 days             | Rapid restore window                        |
| Application logs    | 14 days in logging backend               | Meet troubleshooting needs, respect privacy |

## Implementation Notes

- Configure Kafka via `terraform/modules/kafka` (`retention.ms`).
- S3 lifecycle rules managed in Terraform (`infra/terraform/s3.tf`).
- OpenSearch ILM policy stored in `ops/cost/opensearch_ilm.yaml`.
- Neo4j backups executed by CronJobs (`infra/k8s/backups/`).
- Logs forwarded to central store (DataDog/CloudWatch) with retention per compliance.

## Review Cadence

- Quarterly cost review ensures policies align with storage spend.
- Annual compliance review verifies retention meets legal requirements.
