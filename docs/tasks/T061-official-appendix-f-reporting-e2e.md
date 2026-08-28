---
artifact: task
id: T061
title: Adopt official Appendix-F reporting and prove the production warm-up
status: done
priority: P0
task_type: integration
optional: false
owner: orchestrator
component: C06
depends_on: [T058, T059, T060]
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/contracts/CT-07-kit-artifact-bundle.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
  - docs/decisions/ADR-012-kit-artifact-projection.md
gates: []
claimed_by: root-codex
claim_expires_at: 2026-08-28T16:30:00Z
write_set:
  - README.md
  - common/transport/kit_agreement.py
  - common/transport/kit_artifact_schemas.py
  - common/transport/kit_bundle_validation.py
  - common/transport/kit_consensus.py
  - common/transport/kit_documents.py
  - common/transport/kit_identity.py
  - common/transport/kit_names.py
  - common/transport/kit_result_validation.py
  - common/transport/kit_settlement.py
  - docs/components/C06-reporting-league/PLAN.md
  - docs/components/C06-reporting-league/PRD.md
  - docs/contracts/CT-07-kit-artifact-bundle.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
  - docs/decisions/ADR-012-kit-artifact-projection.md
  - docs/inputs/INPUT_REGISTER.md
  - docs/reporting/README.md
  - docs/reporting/gmail.md
  - docs/reporting/kit-bundle.md
  - docs/reporting/official-appendix-f.md
  - docs/spec/OPEN_QUESTIONS.md
  - docs/tasks/T061-official-appendix-f-reporting-e2e.md
  - scripts/validate_official_artifacts.py
  - scripts/smoke_replay_integration.py
  - src/police_peer/reporting/gmail.py
  - src/police_peer/cli.py
  - src/police_peer/evidence/identity_source.py
  - src/police_peer/evidence/runtime_summary.py
  - src/police_peer/reporting/kit_bundle.py
  - src/police_peer/reporting/kit_bundle_documents.py
  - src/police_peer/reporting/kit_bundle_publish.py
  - src/police_peer/reporting/settlement.py
  - src/police_peer/runner.py
  - src/police_peer/wire/gmail_composition.py
  - src/police_peer/wire/result_agreement.py
  - tests/contract/kit_artifacts/test_kit_documents.py
  - tests/contract/kit_artifacts/test_kit_consensus.py
  - tests/contract/kit_artifacts/test_kit_identity.py
  - tests/contract/kit_artifacts/test_kit_names.py
  - tests/integration/test_gmail_production_composition.py
  - tests/integration/test_kit_bundle_emission.py
  - tests/integration/test_declaration_completeness.py
  - tests/integration/test_llm_gmail_pipeline.py
  - tests/integration/test_mutual_agreement_settles.py
  - tests/integration/test_two_process_smoke.py
  - tests/unit/reporting/test_gmail_kit_result.py
  - tests/unit/evidence/test_step_zero.py
  - tests/unit/wire/test_result_agreement.py
---

# T061 — Official Appendix-F reporting E2E

## Goal

Replace the explicitly non-official kit projection with the pinned instructor v1.1 outward
shape, carry real Git and token evidence, validate and atomically publish 14 files under an
official directory, attach the exact published result bytes, and prove it through the normal
two-process FastMCP runner.

## Acceptance criteria

- [x] All four builders use the official v1.1 outward shape without placeholder evidence.
- [x] Six configs, six logs, one declaration, and one result validate atomically.
- [x] Git, token, timestamps, links, scores, and agreement are checked end to end.
- [x] Outward timestamps use `Asia/Jerusalem` regardless of the machine timezone.
- [x] Gmail dry-run attaches the exact published result bytes.
- [x] A fresh two-process warm-up produces valid official bundles for both peers.
