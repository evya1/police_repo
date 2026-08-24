---
artifact: task
id: T058
title: Exchange and record a mutual result agreement before reporting
status: done
owner: orchestrator
component: C06
depends_on: [T057]
related_requirements: [REPORT-009, LEAGUE-006]
related_decisions: [ADR-013]
related_contracts: [CT-08]
write_set:
  - src/police_peer/wire/result_agreement.py
  - src/police_peer/reporting/settlement.py
  - src/police_peer/reporting/pipeline.py
  - src/police_peer/runner.py
---

# T058 — Mutual result agreement

## Goal

Compare settlements with the opponent after the mutual log audit, before either side is
eligible to report, and refuse reporting when they did not agree.

## What was built

* `wire/result_agreement.py::exchange` — sends our settlement proposal on the CONTROL lane
  (unused by game logic, so a late greeting can never be mistaken for a settlement), polls for
  the opponent's within budget, and decides via `kit_agreement.evaluate`. Never raises into a
  played series: a send or read fault is returned as a non-agreement, not an exception.
* `reporting/settlement.py` — `settle()` wraps the exchange; `publish_kit()` writes the bundle
  with `mutual_agreement.confirmed` set to what was actually agreed, never assumed true.
* `runner.py` — settles immediately after `facade.run()`, i.e. after the series engine's own
  mutual log audit (App. E rule 36 makes the audit a precondition of agreeing). A counted
  series that is not agreed exits 6 without ever calling the reporting pipeline.
* `reporting/pipeline.py::process_and_send` — gained a mandatory `agreement` parameter and
  calls `assert_reportable` before touching the Gmail sender. A counted series without
  agreement raises `NotAgreedError` before any network call.

## Verification

```
uv run pytest tests/unit/wire/test_result_agreement.py            6 passed
uv run pytest tests/integration/test_mutual_agreement_settles.py  3 passed
uv run pytest tests/integration/test_reporting_pipeline.py        6 passed
```

The load-bearing assertion: two independent peers on one loopback channel, running the real
composition path, derive a **byte-identical** consensus digest
(`test_both_sides_derive_a_byte_identical_consensus_digest`) and both report `agreed=True`
(`test_both_peers_reach_agreement_on_a_clean_series`). A perturbed side does not agree, and the
pipeline test proves nothing is transmitted when it does not.

## Notes

The refusal invents no sanction. What the missing-report penalty actually is remains an open
question with the course staff (OPEN-004); `assert_reportable` declines to send rather than
guessing at one.
