# C06 Preparation Analysis

Analyst: deepseek-v4-pro (1 bounded generation, no tools). Reviewer: glm-5.2
(1 bounded generation, no tools) — verdict `approve`, 2026-08-18. This is
implementation-planning evidence for T016–T020; it does not change
`official_status` for OPEN-001, OPEN-004, or OPEN-008, all of which remain
OPEN pending course-staff/lecturer input.

## 1. PLANQ-005 Gmail sender decision

PLANQ-005 is RESOLVED by this analysis (grounded in
docs/evidence/c06-prep-01/inputs/google_gmail_api_python.md, fetched
2026-08-18 from developers.google.com; no OAuth was performed):

- Client packages: google-api-python-client, google-auth-httplib2,
  google-auth-oauthlib — submitted as a structured dependency_request; not
  installed here and not added to pyproject.toml/uv.lock by this task.
- OAuth scope (exact, send-only): https://www.googleapis.com/auth/gmail.send
- Service construction:
  service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
- Send call (exact): service.users().messages().send(userId="me",
  body={"raw": raw_b64}).execute()
  users().messages().send is mandatory; drafts().create or a
  set_content(pretty_json) text body is noncompliant and must never be
  substituted for the JSON attachment.
- MIME/encoding: build with stdlib email.message.EmailMessage; set To/From/
  Subject; attach each finalized report file as a MIME application/json part
  with its official filename; raw_b64 =
  base64.urlsafe_b64encode(message.as_bytes()).decode("ascii"); request body
  {"raw": raw_b64}.
- Credential/token storage: credentials.json and token.json live only in a
  local secret config directory (config/private/gmail/, git-ignored), are
  never logged, never appear in fixtures or docs, and are checked by
  scripts/check_no_secrets.py. An injected filesystem seam supplies the
  paths; no key material is defaulted or committed.
- Token lifecycle: load token.json; if invalid and a refresh token exists,
  creds.refresh(Request()); else InstalledAppFlow.from_client_secrets_file(
  "credentials.json", SCOPES).run_local_server(port=0), persisting token.json.
  This flow is human-gated and never runs in tests.
- Idempotency: Google messages.send has no API-level idempotency key; the
  duplicate-send guard is application-owned: T018 stores a per-game_id
  result-hash sent-state guard, checked and persisted atomically before send;
  a second send for the same verified result is refused.
- Test boundary: live calls never happen; a narrow Callable send seam
  (SendMessageFn = Callable[[bytes], SendOutcome]) is the only Gmail entry
  point, faked in tests to assert exact attachment bytes; every send transits
  the central Gatekeeper (QR-008).

Note: this is a Level-4 implementation decision the project team owns
(explicitly authorized in T030's frontmatter). OPEN-001/OPEN-004/OPEN-008
official_status remains OPEN upstream; nothing above changes that.

## 2. Python architecture (PY profile and module boundaries)

**Profile: `PY-2`.** Reason (verbatim): "C06 contains real stakeholder-facing
business rules — the fixed GAME-013 score table, the six-sub-game invariant
(LEAGUE-001), pairing-eligibility guards (LEAGUE-002/003/004), the diversity
reward (LEAGUE-005), and the M-07 reconciliation algorithm — plus mandated
external I/O (Gmail through the Gatekeeper). That is the PY-2 case of one
maintained application with business rules and external I/O. PY-1 is
insufficient because the component is not a CRUD/data pipeline; PY-3 is
unnecessary because the domain state is derived immutable result records and
the only concurrency is a token-bucket limiter, not business transactions."

**Module boundaries (paths already owned by T016–T020 write sets):**
- `src/police_peer/reporting/schemas.py` — T016 (only after INPUT-001 resolves).
- `config/official/reporting/` — T016 (adopted official templates + sanitized golden fixtures).
- `src/police_peer/infra/external_api_gatekeeper.py` — T017 (the single external-service Gatekeeper, QR-008).
- `src/police_peer/reporting/gmail.py` — T017 (Gmail adapter behind the send seam).
- `src/police_peer/reporting/pipeline.py` + `src/police_peer/reporting/artifacts.py` — T018 (lifecycle orchestration + artifact builders/signers).
- `src/police_peer/league/series.py` + `src/police_peer/league/scoring.py` — T019 (pure deterministic functions).
- `src/police_peer/league/preflight.py` — T020 (pairing-eligibility guards).

**Dependency direction (exact):** `league` imports nothing from `reporting`;
`reporting` consumes `league.scoring` totals ONLY via the CT-06 verified-result
record and never recomputes them; `reporting` and any future provider adapter
depend on `infra.external_api_gatekeeper`; `infra` knows no product types. No
circular imports.

**Side-effect boundary (exact):** the only side-effectful boundary is
`infra.external_api_gatekeeper` plus the injected Gmail send seam; everything
else is pure and deterministic. Live OAuth/send is human-gated and
structurally absent from tests.

**QR-008 conformance (exact sentence):** "Every external-service call in C06
passes through `external_api_gatekeeper.py`; no reporting, league, or
strategy module may import or construct a Google client, and direct service
calls are structurally prevented by the narrow send seam."

## 3. Pattern verdicts (USE / DO_NOT_USE)

| Pattern | Verdict | Concrete reason tied to C06 |
|---|---|---|
| Repository | DO_NOT_USE | Artifacts are derived in-memory from verified CT-06 results; no persistent data-store abstraction exists, and adding one is speculative. |
| Unit of Work | DO_NOT_USE | No transactional multi-aggregate writes; M-07 reconciliation is a comparison algorithm, not a transaction boundary. |
| Service Layer | USE | `reporting/pipeline.py` is the one application use-case (settle → build → send), implemented as plain orchestration functions, not a class hierarchy. |
| rich Domain Model | DO_NOT_USE | Scoring/series are pure deterministic functions over immutable result records; no entity lifecycles warrant a rich object model. |
| Protocol | USE | Narrow `Protocol`/`Callable` seams (send seam, limiter, clock) compose dependencies manually per AGENTS.md; no DI container. |
| Adapter | USE | `reporting/gmail.py` adapts the protocol to Google's API; the OPEN-007 canonical serializer is an adapter at the byte boundary. |
| Aggregate | DO_NOT_USE | The "verified result is terminal" invariant is enforced by pure validation functions, not a cluster-of-entities root. |
| Message Bus | DO_NOT_USE | No in-process event propagation; synchronous pipeline calls suffice. |
| CQRS | DO_NOT_USE | Read and write workloads are identical (derive totals, write the report); splitting them adds cost with no benefit. |
| Event Sourcing | DO_NOT_USE | Replay of step logs is C05's concern; C06 consumes CT-06 final verdicts and never reconstructs state from an event stream. |

## 4. Behavioral test plan (T016–T020)

### T016
(gate note: `INPUT-001 blocks: start` — defer integration tests until the gate resolves)
- **unit** — validators distinguish three distinct failure kinds: `SchemaError`, `SignatureError`, `IdentifierMismatch`; assert each is raised by its own fixture.
- **boundary-adapter** — builders expose the four lifecycle points (declaration, configuration, finalized log, result) and reject premature creation or mutation of a finalized log.
- **integration** — none until INPUT-001 resolves; state this explicitly.
- **failure** — unknown fields and private/secret fields are rejected at validation.
- **security** — no secret content passes into an artifact; check_no_secrets passes against fixtures.
- **determinism** — per-game filenames and reported Git commit strings are byte-identical on replay with injected clock/config.

### T017
(gate note: `PLANQ-005` resolved by this analysis → `sender_choice` criterion unblocked)
- **unit** — token bucket refills per injected clock and refuses over-capacity; concurrency bound is enforced; queue overflow is explicit; DOS lockout threshold flips the pipeline locked; quota decrement reaches zero.
- **boundary-adapter (Gmail)** — a fake send seam captures the exact `raw` bytes; an OAuth scope check rejects any broader granted scope; a draft-substitute or message-body-text path fails the compliance check.
- **integration** — Gatekeeper + Gmail adapter are wired so every send transits the single facade; a future provider adapter must route through the same facade without changing Gmail behavior.
- **failure** — 429 (backoff, not blind retry), quota-exhausted, expired-token, invalid-recipient, duplicate-send, and network-error paths each return a distinct failure outcome.
- **security** — credentials.json/token.json are absent from fixtures and logs; check_no_secrets passes.
- **determinism** — backoff schedule and bucket state are deterministic under an injected clock/RNG.

### T018
(gate note: `OPEN-004 blocks: criterion` on `sanction_settlement` — implement the conservative guard only)
- **unit** — artifact totals derive strictly from CT-06 records + the fixed GAME-013 table; the idempotent sent-state guard refuses a second send for the same `game_id`.
- **boundary-adapter** — the exact MIME attachment bytes passed to a mock are asserted byte-for-byte; exactly one send per settled series.
- **integration** — declaration → per-sub-game configuration → finalized log → result is produced in lifecycle order, then exactly one send fires.
- **failure** — missing, incomplete, or conflicting required reports reach the explicit unsettled state with preserved evidence (M-07); tampered/schema-invalid records are refused.
- **security** — signature verification precedes any send; no plaintext report is ever accepted.
- **determinism** — with seeded verified records and injected timestamp/commit values, artifact bytes are identical across runs.

### T019
(gate note: `OPEN-008 blocks: criterion` on `series_aggregation` — add/replace are differential only)
- **unit (scoring)** — every GAME-013 row asserted directly: CAPTURE Police 20 / Thief 5; SURVIVAL Police 5 / Thief 10; TECHNICAL_LOSS 0/0; tie value 2.
- **unit (series)** — exactly six isolated sub-games, clean state reset, unique config/log identities; additive tie per the OPEN-008 convention; series-replace asserted as a rejected differential alternative.
- **boundary-adapter** — totals derive from CT-06 records only, never from recomputation.
- **integration** — the same verified sub-game list is the single source feeding both totals and the T018 report input.
- **failure** — TECHNICAL_LOSS/TAMPERED outcomes cannot be converted to clean or tie scores.
- **determinism** — the same verified list always yields the same totals.

### T020
(gate note: `G-LIVE blocks: criterion` on `pairing_preflight` — live endpoint checks wait)
- **unit (guards)** — refuse an eleventh counted match; refuse a second counted match against the same opponent; warm-up and counted modes are discrete and cannot share report state.
- **unit (declarations)** — signed prior counted-match declarations are compared and retained.
- **integration** — preflight pass/fail cases run against synthetic double data; live endpoint data required only for the G-LIVE criterion.
- **failure** — a false prior-match declaration returns the LEAGUE-004 disqualification verdict.
- **security** — hardware/version/token evidence is complete and contains no local fairness-score formula computation (LEAGUE-007).
- **determinism** — identical opponent history yields an identical eligibility verdict.

## 5. Implementation plan (T016–T020)

### T016
Status: `blocks: start` on INPUT-001; never begin speculatively. When the gate
resolves: adopt the four official templates unmodified into
`config/official/reporting/`; record authority, version, safe hash, and
verification status in INPUT_REGISTER; implement `schemas.py` validators
returning the three distinct errors from §4; builders expose the four
lifecycle points; golden tests from sanitized official templates; candidate
layouts quarantined from production config. Error model: `SchemaError`,
`SignatureError`, `IdentifierMismatch`. Dependency requests: none.

### T017
Modules `external_api_gatekeeper.py` (facade: token bucket, queue, DOS
lockout, backoff, optional quota) and `reporting/gmail.py` (adapter).
Configuration-driven limits (private TOML defaults, shared JSON overrides).
Gmail adapter builds the RFC 2822 MIME message per §1 and calls
`users().messages().send`; scope check rejects broader grants. Backoff policy
(exact): on HTTP 429 only, exponential backoff with full jitter, base 2.0 s,
max 3 attempts; queue overflow and DOS lockout do not retry. Resource
lifecycle: bounded queue with timeout/cancellation; blocking send executed
off the event loop via an injected executor seam. Error model: `RateLimited`,
`QueueOverflow`, `DosLocked`, `BackoffExceeded`, `QuotaExhausted`,
`InvalidRecipient`, `TokenExpired`, `DuplicateSend`, `NetworkError`.
Dependency request: structured `dependency_request` for
`google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib` (a
separate authorized dependency-integration step must land them before T017
tests run).

### T018
`artifacts.py` builds/signs the four artifacts from CT-06 and enforces
immutability of a finalized log; `pipeline.py` orchestrates settle → M-07
reconcile → build → one Gatekeeper send. OPEN-004's sanction criterion waits;
implement the conservative unsettled state only. Idempotency: persist the
per-`game_id` result-hash sent guard before send. Exact attachment bytes
asserted against a fake send. Dependency requests: none beyond T016/T017
outputs.

### T019
`scoring.py` exposes one pure function `score_subgame(outcome:
SubGameOutcome) -> Scores` implementing exactly: CAPTURE → Police 20, Thief
5; SURVIVAL → Police 5, Thief 10; TECHNICAL_LOSS → 0/0; TAMPERED → 0/0; no
local formula exported. `series.py` exposes `build_series(sub_games) ->
SeriesTotals` enforcing exactly six sub-games, role alternation per the
OPEN-008 operational convention (three each), clean reset per sub-game,
unique config/log identities, additive tie (LEAGUE-006 adds the fixed 2),
diversity reward 10 only for a qualifying new-opponent win (LEAGUE-005).
Series-replace is implemented only as a rejected differential alternative,
never selectable for counted play. Error model: `InvalidSubGameCount`,
`RoleScheduleViolation`.

### T020
`preflight.py` provides pure guards over opponent history and signed
declarations: enforce 2..10 counted matches total (LEAGUE-002), at most one
counted match per opponent (LEAGUE-003), truthful prior-count declarations
signed/compared/retained (LEAGUE-004), warm-up/counted mode separation, and
hardware/version/token evidence collection with **no** local normalization
formula (LEAGUE-007). Live endpoint checks are behind the G-LIVE criterion
and must fail closed until real opponent/endpoint data is present. Error
model: `TooManyCountedMatches`, `DuplicateOpponent`, `DeclarationMismatch`.

## 6. Task execution order

1. T030 (this analysis) resolves PLANQ-005.
2. Orchestrator-owned dependency-integration step adds the three Google
   packages named in §1; this gates T017's test run.
3. T019 — claimable once T004, T010, T013 are done; parallel-safe.
4. T017 — claimable once T002, T003 are done and step 2 is complete;
   parallel-safe; the formerly waiting sender_choice criterion is now
   unblocked by PLANQ-005 resolution.
5. T016 — NOT claimable: INPUT-001 gates blocks: start; it must not begin
   until the official templates arrive.
6. T018 — after T012, T013, T015, T016, and T017 are all done; not
   parallel-safe.
7. T020 — after T018 and T019 are done; parallel-safe; the pairing_preflight
   criterion waits on G-LIVE.

Note: T002 and T003 are currently NOT complete in either repository
(T002 status=ready/not started, T003 status=blocked), so T017 is not
currently claimable either, despite step 4 above describing its eligibility
condition. This is the exact blocker: **T002, T003**.

## 7. Canonical GitHub issue bodies

Canonical body template (fixed field order, reused verbatim across all six
bodies): **Title:** / **Task ID:** / **Component:** / **Priority:** /
**Requirements:** / **Status:** / **Dependencies:** / **Gates:** / **Scope:** /
**Acceptance checkpoints:** / **Evidence:**
## parent

**Title:** C06 — adopt official schemas, implement Gatekeeper & Gmail
pipeline, integrate signed reporting, and implement series/scoring + pairing
guards (children T016–T020)
**Task ID:** C06 parent epic
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** REPORT-001..013, LEAGUE-001..007, GAME-013, CFG-009,
CFG-010, QR-008, QR-018, SEC-010
**Status:** blocked — children remain blocked/unstarted until their gates
resolve
**Dependencies:** T002, T003, T004, T010, T012, T013, T015 (cross-component);
INPUT-001 (official templates)
**Gates:** PLANQ-005 (resolved by T030); OPEN-001 (blocks T016 start),
OPEN-004 (blocks sanction_settlement criterion), OPEN-008 (blocks
series_aggregation criterion), G-LIVE (blocks pairing_preflight criterion)
**Scope:** reporting pipeline, Gatekeeper/Gmail adapter, series/scoring, and
league pairing guards
**Acceptance checkpoints:** every child merges only after its own gates and
dependencies pass
**Evidence:** per-child pytest/ruff commands listed in the child issues

## T016

**Title:** T016 — Adopt official report artifact schemas
**Task ID:** T016
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** CFG-009, CFG-010, REPORT-005, REPORT-006, REPORT-007,
REPORT-008, REPORT-009
**Status:** blocked — INPUT-001 gates blocks: start
**Dependencies:** none
**Gates:** INPUT-001 (input, blocks: start, scope schema_adoption)
**Scope:** adopt the four official JSON templates unmodified; validators and
lifecycle-aware builders
**Acceptance checkpoints:** template receipt/hash/verification recorded in the
input register; validators distinguish schema/signature/identifier failures;
deterministic filenames and reported Git commits; no private secrets; builders
only at the four lifecycle points; golden tests from sanitized official
templates; candidate layouts quarantined
**Evidence:** uv run pytest tests/contract/report_schemas ; uv run ruff check
src/police_peer/reporting/schemas.py tests/contract/report_schemas

## T017

**Title:** T017 — Implement external-service Gatekeeper and Gmail adapter
**Task ID:** T017
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** SEC-010, REPORT-001, REPORT-002, REPORT-003, REPORT-004,
REPORT-010, REPORT-011, REPORT-012, REPORT-013, QR-008
**Status:** blocked — depends on T002/T003 and the dependency-integration step
named in T030 §1
**Dependencies:** T002, T003
**Gates:** PLANQ-005 (decision, blocks: criterion scope sender_choice) —
resolved by T030's analysis: send-only gmail.send scope, users().messages()
.send, EmailMessage + base64url attachment, application-level duplicate-send
guard, credentials/token local-only and ignored, tests use doubles
**Scope:** central config-driven Gatekeeper plus the mandatory send-only Gmail
adapter reachable only through it (QR-008)
**Acceptance checkpoints:** OAuth requests only gmail.send and rejects broader
grants; adapter uses messages.send and cannot draft-substitute; all sends
transit the single Gatekeeper; token bucket/concurrency/queue/backoff/DOS/
quota config-driven; credentials.json and token.json are git-ignored and never logged;
429/quota/expired-token/invalid-recipient/duplicate-send/network-error use
doubles
**Evidence:** uv run pytest tests/unit/infra/test_external_api_gatekeeper.py
tests/unit/reporting/test_gmail.py ; uv run python scripts/check_no_secrets.py

## T018

**Title:** T018 — Integrate signed reporting
**Task ID:** T018
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** REPORT-001, REPORT-004, REPORT-005, REPORT-006, REPORT-007,
REPORT-008, REPORT-009
**Status:** blocked — depends on T012, T013, T015, T016, T017
**Dependencies:** T012, T013, T015, T016, T017
**Gates:** OPEN-004 (open, blocks: criterion scope sanction_settlement) —
until it resolves, missing/incomplete/conflicting reports reach the
conservative unsettled state with preserved evidence and are never
auto-settled or auto-sanctioned
**Scope:** settled legal series produces mutually consistent signed artifacts
and exactly one independent automated report through the Gatekeeper
**Acceptance checkpoints:** totals derived from verified records + the fixed
scoring table; lifecycle order + immutable finalized evidence; identifiers/
repos/commits/hardware/tokens/timestamps reconcile; idempotent single send;
unsettled/tampered/schema-invalid/peer-inconsistent refuse per OPEN-004;
exact attachment bytes asserted to a mock
**Evidence:** uv run pytest tests/integration/test_reporting_pipeline.py

## T019

**Title:** T019 — Implement series and scoring
**Task ID:** T019
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** GAME-013, LEAGUE-001, LEAGUE-005, LEAGUE-006
**Status:** blocked — depends on T004, T010, T013
**Dependencies:** T004, T010, T013
**Gates:** OPEN-008 (open, blocks: criterion scope series_aggregation) — the
T030 analysis uses the recorded operational convention only: six sub-games,
alternating roles three each, clean reset, additive tie
**Scope:** six isolated counted sub-games and the fixed score table, tie and
diversity derivations
**Acceptance checkpoints:** exactly six configured sub-games with clean reset
and unique identities; all GAME-013 rows assert directly; additive tie per
the convention while series-replace stays a rejected differential alternative;
diversity reward only for qualifying new-opponent wins; technical-loss/tamper
non-convertible; one verified sub-game list feeds totals and report input
**Evidence:** uv run pytest tests/unit/league/test_series.py
tests/unit/league/test_scoring.py

## T020

**Title:** T020 — Implement league pairing guards
**Task ID:** T020
**Component:** C06-reporting-league
**Priority:** P0
**Requirements:** LEAGUE-002, LEAGUE-003, LEAGUE-004, LEAGUE-007
**Status:** blocked — depends on T018, T019
**Dependencies:** T018, T019
**Gates:** G-LIVE (input gate, blocks: criterion scope pairing_preflight) —
live endpoint acceptance waits; local guard logic is testable now against
synthetic doubles
**Scope:** counted-match eligibility, honest declarations, and fairness
evidence without a local normalization formula
**Acceptance checkpoints:** refuse an eleventh counted match and a second
counted match per opponent; two-distinct-opponent obligation tracked, not
faked; signed prior-count declarations compared and retained; warm-up/counted
modes cannot share report state; hardware/version/token evidence complete with
no local fairness-score formula; live preflight passes only with real
opponent/endpoint data
**Evidence:** uv run pytest tests/unit/league/test_pairing_guards.py
tests/integration/test_preflight.py