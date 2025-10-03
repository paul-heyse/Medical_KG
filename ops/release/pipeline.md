# Deployment Pipeline (Idempotent Steps)

Documented sequence for staging → production promotions. Steps are idempotent; rerunning preserves state if partially complete.

## 1. Infrastructure (Terraform)

```bash
cd infra/terraform
terraform init
terraform plan -var-file=${ENV}.tfvars -out=tfplan
terraform apply tfplan
```

- Provision changes (node pools, managed services) separately from application deploy.
- Store plan output as artefact in release ticket.

## 2. Configuration & Secrets

```bash
# Render config from templates (no secrets committed)
python scripts/config/render.py --env ${ENV} --output build/config

# Sync secrets from Vault/AWS SM
task sync-secrets ENV=${ENV}
```

- Configmaps/Secrets applied via Helm values.
- Verify diff with `helm get values medkg-api -n medkg` before applying.

## 3. Helm Deploy (API + Workers)

```bash
helm upgrade --install medkg-api deploy/helm/medkg \
  -n medkg \
  -f deploy/helm/values-${ENV}.yaml \
  --set image.tag=${GIT_SHA} \
  --wait --timeout 10m
```

- `--wait` ensures readiness gates and liveness probes succeed.
- Helm release is idempotent; rerun with same values to reconcile drift.

## 4. Database Migrations

```bash
python -m Medical_KG.infrastructure.migrate \
  --config build/config/${ENV}.yaml \
  --dry-run false
```

- Migration script records checksum in `schema_migrations` to prevent duplicate execution.
- Failing migrations auto-rollback (wrap in transaction) and exit non-zero.

## 5. Verification Hooks

```bash
python ops/e2e/run_verification.py --mode live --env ${ENV} --base-url https://api-${ENV}.medkg.example.com --report reports/e2e-${ENV}.json
python ops/load_test/check_thresholds.py reports/load-test-${ENV}/report.html --budget ops/load_test/budget.yaml --profile burst
```

- Upload reports to artefact storage (`s3://medkg-release-artifacts/${RELEASE_ID}/`).
- Gate promotion on passing verification.

## 6. Rollback Procedure

- Redeploy previous Helm chart (`helm rollback medkg-api <REVISION>`).
- Restore config from prior commit and `kubectl rollout restart deployment/medkg-api`.
- For data regressions: restore latest snapshot via `ops/runbooks/07-datastore-failover.md`.

## 7. Post-Deploy Tasks

- Announce completion in `#ops` and update status page.
- Monitor `Medical KG - Pipeline Overview` dashboard for 30 minutes.
- File post-deployment notes (issues, follow-ups) in release ticket.
