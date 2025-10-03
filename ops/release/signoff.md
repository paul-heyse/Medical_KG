# Release Sign-Off Workflow

## Participants

- **Engineering Lead** – owns technical delivery and rollback.
- **Operations Lead** – coordinates deployment window, monitors metrics.
- **Clinical/Domain Lead** – validates medical impact and stakeholder comms.
- **Security/Compliance** – confirms licensing, privacy, vulnerability posture.

## Workflow

1. **Kickoff (T-48h)**
   - Review release notes + change list.
   - Verify checklist owners assigned (`ops/release/checklist.md`).
   - Schedule deployment window and communicate in `#ops`.
2. **Readiness Review (T-4h)**
   - Walk through readiness checklist.
   - Confirm verification runs scheduled.
   - Capture go/no-go decision in release ticket.
3. **Deployment Window**
   - Operations lead runs pipeline (`ops/release/pipeline.md`).
   - Engineering lead monitors logs/traces.
   - Domain lead on standby for SME questions.
4. **Validation (T+30m)**
   - Verify dashboards stable (latency, error rate, SHACL, GPU).
   - Execute live E2E harness.
   - Publish "deployment complete" update.
5. **Postmortem (within 48h if issues)**
   - Document timeline, root cause, follow-up actions.
   - Update runbooks/automation based on lessons.

## Sign-Off Template

```
Release: <release-id>
Environment: staging | production
Date: 2024-10-03

Engineering Lead: ________   ✅ yes / ❌ no (notes)
Operations Lead:  ________   ✅ yes / ❌ no (notes)
Clinical Lead:    ________   ✅ yes / ❌ no (notes)
Security Lead:    ________   ✅ yes / ❌ no (notes)

Risks Accepted: ______________________
Rollback Plan: _______________________
Verification Artifacts: s3://medkg-release-artifacts/<release-id>/
```

Store completed sign-off in the release ticket and link from the deployment PR.
