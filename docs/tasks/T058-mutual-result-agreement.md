---
artifact: task
id: T058
title: Mutual result agreement before reporting
status: done
owner: orchestrator
component: C06
depends_on: [T057]
related_requirements: [REPORT-005, REPORT-006, REPORT-007]
related_decisions: [ADR-013]
related_contracts: [CT-08]
write_set:
  - src/police_peer/wire/result_agreement.py
  - src/police_peer/reporting/kit_bundle.py
  - src/police_peer/runner.py
  - src/police_peer/reporting/pipeline.py
---

# T058 — Mutual result agreement before reporting

## Goal

Wave 1's `mutual_agreement` block was a locally-computed digest with no counter-proposal behind
it. This task makes the agreement real: both peers exchange their consensus digest exactly
once, after the series' own mutual audit, and nothing downstream may claim an agreement that
did not happen.

## What was built

* `wire/result_agreement.py::exchange` — sends our `AgreementProposal` once over the existing
  control channel (`send_control`/`poll_control` — the same generic lane the series transport
  already exposes for out-of-band messages), waits up to a budget for the opponent's, and
  evaluates via `kit_agreement.evaluate`. Never raises into the game loop: a transport fault, a
  malformed reply, or silence all become `AgreementOutcome(agreed=False, ...)`.
* `runner.py` runs the exchange after `result.settled` (after the series engine's own mutual
  log audit — App. E rule 36 makes that audit a precondition of agreeing), then publishes the
  kit bundle with `mutual_agreement.confirmed=outcome.agreed`. A counted series without
  agreement returns exit code 6 — the bundle is still published, honestly marked
  `confirmed: false`, never silently dropped.
* `reporting/pipeline.py::process_and_send` gained a mandatory `agreement: AgreementOutcome`
  parameter and refuses to transmit unless `agreement.agreed` — the existing conservative
  `settle_series` guard is untouched and this is an additional, independent gate.

## Acceptance

```
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
```

`tests/integration/test_mutual_agreement_settles.py` runs a real two-sided exchange over the
loopback control channel and confirms both matching and perturbed rows produce identical
outcomes and digests on both ends.
