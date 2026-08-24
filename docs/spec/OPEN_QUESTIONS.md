# Open Questions, Late Inputs, and Implementation Decisions

These are active blockers and confirmations, not permission to guess. T001 records an arriving authoritative input in `INPUT_REGISTER.md`, verifies it, updates the affected `OPEN-*` entries, and reconciles derived artifacts. Input receipt does not create a Change Request unless accepting the information changes an already-approved canonical product requirement or PRD contract.

## Categories used in this register

- **Official requirement** — a behavior explicitly required by the authoritative project specification, an official course artifact, the official software-quality guide, or a later written lecturer clarification. Nothing else may be labeled one.
- **Operational convention** — a concrete project decision taken because the official requirements leave a detail undefined or admit several valid choices, while implementation needs one deterministic choice for interoperability, testing, execution, serialization, or reporting. A convention is binding for this implementation, is never presented as a course requirement, carries a precise contract and verification, and is replaced if a later authoritative clarification requires other behavior.
- **Implementation decision** — an ordinary internal engineering choice that interprets no unresolved course rule, such as package layout or an internal interface shape. These are not tracked here.
- **Unresolved official input** — something that genuinely requires an external artifact, a live opponent/team/submission value, or an authoritative clarification, and cannot safely be decided locally.

## Two independent axes

`official_status` records whether the course/lecturer has actually closed the question. Only a verified official answer moves it to `RESOLVED`. `implementation_status` records how much local work can proceed without that answer. The two are independent: an item can remain `official_status: OPEN` while its `implementation_status` narrows to a specific, named criterion instead of blocking an entire task.

Allowed `implementation_status` values:

- `RESOLVED_LOCALLY` — the authoritative material already fully determines every implementable behavior; no task waits on this item.
- `DIFFERENTIAL_TESTS_ONLY` — implementation proceeds using the compatibility-matrix pattern (candidate behaviors compared, none selected as production default); only the final lock/selection criterion waits.
- `OPERATIONAL_CONVENTION` — a recorded operational convention determines every implementable behavior; only the claim of official correctness, and any named confirmation gate, still wait.
- `LATE_RUNTIME_INPUT` — the input is expected only late in the project lifecycle (team confirmation, opponent, submission form); it does not block early work.
- `HARD_BLOCK` — no local work may substitute for the missing answer at the named scope.

`latest_safe_resolution_gate` names the acceptance criterion or integration gate (see `docs/tasks/T###` `gates:` entries and the project-level integration plan) beyond which the item must be resolved. `blocks` / `does_not_block` state the scope precisely, replacing a flat "this open item blocks this task" reading.

## Active OPEN items

| ID | Type | Question / missing input | Impact | Required next action | Owner |
|---|---|---|---|---|---|
| OPEN-001 | MISSING OFFICIAL INPUT | The four official attached JSON templates/schemas for the declaration, per-sub-game configuration, log, and result artifacts, and their exact canonical rules, have not been supplied. Runtime instances are produced during the lifecycle: declaration before the series, configuration before each sub-game, log during and finalized after each sub-game, and result after verified series settlement. **See "OPEN-001 local artifact contract" below; `official_status` remains OPEN.** | Narrowed: blocks final authoritative artifact compliance and cross-team artifact verification. Does not block the reporting architecture, the lifecycle builders, the validators, or their tests, which are developed against the project artifact contract. It does not imply that completed match instances should already exist. | Obtain the original declaration, configuration, log, and result templates/schemas; do not present a locally defined field contract or canonical byte rule as the official one. | orchestrator + project team/lecturer |
| OPEN-003 | TEAM INPUT | Confirmed non-secret metadata: team name `ZeroOne`, team number `01`, GitHub handles `evya1` and `Us5rName`, and the two role repository URLs (`https://github.com/evya1/police_repo`, `https://github.com/evya1/thief_repo`). An eight-character candidate group code `ZeroOne1` appears in the role READMEs and is **not yet confirmed** against a human-approved team record. Still unknown: the final opponent identity, the public MCP endpoints, the tunnel procedure, and counted-game runtime values. | Blocks live endpoints, counted play, final reporting identifiers, and submission. Does not block repository planning or local implementation. | Confirm the group code against a human-approved team record before it is used in any submitted artifact; it stays a candidate until then. Collect the remaining live values as they become real. Never infer an opponent, endpoint, tunnel URL, or counted-game value, and never add government identifiers to repository artifacts. | orchestrator + project team/lecturer |
| OPEN-004 | SOURCE CONTRADICTION | §9.3.3 says the non-reporting side receives no credit, while Appendix E rule 35 says a missing or conflicting report invalidates the game and gives both sides 0. | Blocks the final report-refusal/sanction behavior and T018 settlement. | Ask the lecturer which sanction governs. Until then apply the conservative guard below; do not implement a punishment beyond what the authoritative requirements establish. | orchestrator + project team/lecturer |
| OPEN-005 | SOURCE AMBIGUITY | The Minimum status for operational maxima such as `requests_per_minute` or `concurrent_requests` does not unambiguously define the 'harder' direction. **See "OPEN-005 local resolution" below; `official_status` remains OPEN.** | Narrowed: blocks only labeling or approving a proposed negotiated change to an operational Minimum parameter. Does not block CFG-005/CFG-007 validation, default-value operation, the Game Core configuration boundary (T003), or C04 retry/timeout behavior (T011, T017). | Use printed defaults unless both teams document an agreement; obtain lecturer guidance before labeling a change as "harder" or "easier". | orchestrator + project team/lecturer |
| OPEN-006 | MISSING OFFICIAL INPUT | Whether Step 0 requires any course-supplied credential beyond the declaration, sealing, and signing mechanism the project already documents. No authoritative artifact defines such a credential, and none may be assumed to exist. | Blocks only the criterion that Step 0 uses a course-supplied credential, if one turns out to be required. Does not block Step 0 implementation, which proceeds against the documented project mechanism with a clean extension point. | Ask whether any course-supplied signing material or distribution procedure exists. Do not invent, fabricate, or commit key material of any kind. | orchestrator + project team/lecturer |
| OPEN-007 | SCHEMA AMBIGUITY | The source binds at least State/Move/Intent/Nonce but describes a richer record; nonce placement, Unicode escaping, canonical separators, report-consensus signature scope and form, and the `game_uid`/`game_id` relationship are not fixed by any available official file. **See "OPEN-007 canonical serialization convention" below; `official_status` remains OPEN.** | Narrowed: blocks the claim that the implemented bytes are the officially required bytes, and the final report envelope. Does not block the Commit-Reveal primitives, the canonical serializer, the audit path, or their golden vectors, which are built against the recorded convention. | Obtain the official schemas or a written clarification; until then implement the convention below and keep it behind the adapter boundary. | orchestrator + project team/lecturer |
| OPEN-008 | TERMINOLOGY / SERIES SEMANTICS | The terms game, match, series, and sub-game overlap; Appendix F fixes six sub-games but does not state role assignment or alternation, and the cumulative-tie wording does not unambiguously say whether the score of 2 replaces or is added to accumulated points. **See "OPEN-008 series execution convention" below; `official_status` remains OPEN.** | Narrowed: blocks the counted-play role schedule, the aggregation labels used in official artifacts, and tie settlement in a counted series. Does not block the binding count of six, the tie value 2, the fixed GAME-013 score table, or local series execution and testing. | Confirm role assignment, alternation, and tie aggregation before counted play; retain the binding numeric values. | orchestrator + project team/lecturer |
| OPEN-009 | SOURCE AMBIGUITY | Section 4.3 states that scent intensity is in `[0, 0.9]` and gives `tau_ij(t+1)=max(0,(1-rho)tau_ij(t)+delta_tau_ij)`. Repeated emission can exceed 0.9, but no upper clamp, replacement, or merge rule is stated, and no source fixes whether decay applies before or after a same-turn deposit, or how rounding is handled. **See "OPEN-009 scent recurrence convention" below; `official_status` remains OPEN.** | Narrowed: blocks only the claim that an implemented profile is the officially correct reading of section 4.3, and the confirmation step required before counted play. Does not block implementing scent (T005), selecting the default profile, generating or declaring the model lock, local testing, or uncounted external play. | Obtain lecturer confirmation of saturation, merge rule, and update order; record a numeric repeated-emission example and confirm the selected profile before counted play. Never label either profile as the official reading. | orchestrator + project team/lecturer |
| OPEN-010 | HUMAN CONFIRMATION | The final team, runtime, and submission metadata has not been confirmed against a human-approved team record. | Blocks counted play and final submission. It does not block local planning, implementation, or repository publication. | Before counted play and before final submission, confirm the team name `ZeroOne`, team number `01`, GitHub handles `evya1` and `Us5rName`, the group code, the reported repository URLs and commit identifiers, and the hardware/model declaration fields against a human-approved record. Preserve the recorded values until then; do not guess replacements or add private identity data. | project team |
| OPEN-011 | SOURCE AMBIGUITY | GAME-014 fixes a move cap and a survival threshold that both default to 35, but no source states whether they are one termination event or two, which outcome and score a move-cap exhaustion produces, or whether one counted move is a full round in which both sides act or a single half-turn. | Blocks the terminal-outcome map for a move-cap exhaustion, sub-game settlement, and any counted play whose two values diverge. The binding minimum of 35 for each value and the GAME-013 score table are unaffected. | Ask the lecturer whether reaching the move cap yields the GAME-013 survival score or a technical loss, and whether the count is per round or per half-turn. Until then keep both readings as explicit differential tests, refuse to score a move-cap exhaustion rather than guessing, and refuse to start a sub-game whose two values diverge. | orchestrator + project team/lecturer |

## OPEN-001 local artifact contract (operational convention)

The official templates are still required, and no locally defined artifact may be presented as one of them. To keep the reporting architecture buildable and verifiable in the meantime, the project defines its own artifact contract.

**Convention.** The four lifecycle artifacts — declaration, per-sub-game configuration, log, and result — are produced by dedicated builders against a project-defined schema held in `config/official/reporting/`, serialized with the canonical form recorded under OPEN-007 below, and validated by schema, signature, and cross-artifact identifier checks. Each artifact is created only at its lifecycle point, and a finalized log is immutable.

**Scope.** This convention is sufficient for development, unit and contract testing, and local end-to-end runs. It is not sufficient for counted reporting.

**Verification.** Builders, validators, and cross-artifact reconciliation are proven against committed fixtures for the project contract. When the official templates arrive, they replace the project schema at the same boundary and the same test suite is re-run against them.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: before-counted-reporting`; `blocks` is narrowed to final authoritative artifact compliance.

## OPEN-004 conservative settlement guard (operational convention)

The official contradiction stays open, and no punishment beyond the authoritative requirements is implemented.

**Convention.** A series result is finalized automatically only when both required reports exist and are mutually consistent. Missing, incomplete, or conflicting required reports produce an explicit unsettled state with preserved evidence; they never produce an automatically settled valid result, and they never select a sanction on their own.

**Verification.** T018 tests assert that each of the missing, incomplete, and conflicting cases reaches the unsettled state rather than a scored outcome.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: report_reconciliation`.

## OPEN-005 local resolution

**Evidence.** `CFG-005` (Appendix E rule 12; Appendix F status definitions; PDF p. 144, 151, 155) states, verbatim: *"A Fixed value is immutable; a Negotiated value may be freely agreed and defaults when no agreement exists; a Minimum value cannot fall below its threshold and may be made harder only by agreement."* This is corroborated verbatim in `final_project_requirements_en.md:192` and `:402` ("`Minimum` is a floor that may not be weakened"), and in the Hebrew audit register row `AUD-052`.

**Finding.** This authoritative text establishes two independently enforceable rules that together fully determine every implementable behavior for the nine `CFG-007` Minimum parameters: (1) an absolute floor — a configured value below the printed threshold is rejected unconditionally, with no agreement able to weaken it; (2) an agreement precondition — any deviation from the printed default requires recorded mutual agreement. Under these two rules, configuration validation and every runtime default are fully specified without knowing which direction "harder" points. Since rule 2 already requires agreement for a change in either direction, the missing directional label changes no enforceable behavior.

**What remains open:** only the semantic label itself — whether "harder" is stated for descriptive clarity in a future negotiation record, not whether a change is legal. `official_status` therefore **stays OPEN**; the authoritative material does not define the directional semantics, and this analysis does not close an official question.

**Resolution applied.** `implementation_status: RESOLVED_LOCALLY`; `latest_safe_resolution_gate: before-negotiated-change-to-a-Minimum-parameter`; `blocks` is narrowed to labeling or approving such a proposed change. This item is not an implementation blocker.

## OPEN-006 Step 0 mechanism (operational convention)

No authoritative artifact defines a course-supplied Step 0 signing credential, and none is assumed to exist. The earlier assumption that one had already been issued was unsupported and has been withdrawn.

**Convention.** Step 0 is implemented against the project's documented declaration, sealing, and signing mechanism: the required hardware, model, version, team, sub-game, and commit fields are collected before the first move, canonicalized under the OPEN-007 convention, and sealed through the single integrity boundary. The signing material is supplied through one narrow, injected credential seam with no default value, so a later authoritative credential requirement is satisfied by configuring that seam rather than by changing the Step 0 record or the integrity path.

**Scope.** No credential is fabricated, generated as a stand-in for an authorized one, or committed. Locally generated nonces, hashes, and example signature fields are not a substitute for an authorized credential and are never described as one.

**Verification.** T013 tests prove the full field set is collected and sealed before the first move, that a missing or unverifiable commit or configuration version blocks counted play, and that the credential seam is injected rather than defaulted.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: before-counted-play`.

## OPEN-007 canonical serialization convention (operational convention)

The official byte contract is still missing and the ambiguity stays visible. The implementation nevertheless needs one deterministic byte form, because two peers must independently produce identical verification results.

**Canonical serialization.**

- UTF-8 encoding, no byte-order mark.
- Object keys sorted by Unicode code point, ascending.
- Compact separators: `,` between items and `:` between key and value, with no other whitespace.
- Non-ASCII characters are emitted literally, never as `\u` escapes.
- Floats use the shortest representation that round-trips exactly; a value that fails shortest round-trip is rejected rather than silently re-formatted.
- Integers and floats are distinct; an integral float is not narrowed to an integer.
- No trailing newline.

**Commitment construction.** The commitment for one step is `SHA-256` over `canonical(payload) || "|" || nonce`, where `payload` is the `{State, Move, Intent}` triple in canonical form, `||` is byte concatenation, `"|"` is the single-byte U+007C separator, and `nonce` is the step's fresh nonce in its transmitted textual form. The digest is compared as a 64-character lowercase hexadecimal string; uppercase is a mismatch, because the value is compared as a string.

**Ordering.** Commit precedes acknowledgement, acknowledgement precedes reveal, and the full audit runs only after the last reveal of a sub-game. The nonce is never transmitted or logged before the audit phase. Replay follows recorded step order; a missing, extra, reordered, or mutated step is an integrity failure, not a repairable condition.

**Identifiers.** `game_uid` is the series-scoped identifier carried in the declaration and in every artifact; `game_id` is the sub-game-scoped identifier. Both are compared as exact strings. Their relationship to the eventual official fields is unresolved, so both are produced through the adapter boundary rather than assumed by the domain.

**Verification.** Deterministic golden vectors committed under T008 cover the canonical form (key ordering, compact separators, literal non-ASCII, float round-trip), the commitment construction, and the sealed terms and identifier signatures built on it. The vectors are byte-exact: a divergence fails the local suite rather than an opponent's audit. Both role repositories run the same vectors, which is what makes two independent peers produce identical verification results.

**Not claimed.** This convention is not the official byte contract. When the official schemas arrive they replace it at the adapter boundary, and the differential fixtures for compact-versus-spaced JSON, nonce-inside versus nonce-appended, Unicode, float, key-order, and signature-insertion variants remain as rejection tests.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: cross_peer_vectors`.

## OPEN-008 series execution convention (operational convention)

Every explicitly required series behavior is preserved: exactly six sub-games per series, the fixed tie value of 2, and the GAME-013 score table. Only the details the source leaves undefined are decided here.

**Convention.**

- Roles alternate across the six sub-games, starting from this repository's natural role, so each side plays each role three times in a series.
- Each sub-game runs from a clean state with its own configuration and log identity; no state carries across sub-games.
- Series totals accumulate per sub-game, and the tie value is **added** to the accumulated total rather than replacing it.
- A technical-loss or tampered outcome scores zero for both sides and can never be converted into a clean or tie outcome.

**Verification.** T019 tests assert the six-sub-game count, the alternation schedule, clean state reset, unique configuration/log identities, and the additive tie application, and keep series-replace as an explicit rejected alternative.

**Counted-play gate.** Role assignment, alternation, and tie aggregation materially affect counted scoring. Before counted play, the schedule and the tie rule are confirmed against the official reporting files or a lecturer answer; the convention above governs local execution only until then.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: before-counted-play`.

## OPEN-009 scent recurrence convention (operational convention)

**What did not change.** Section 4.3 still states an intensity range of `[0, 0.9]` and the recurrence `tau_ij(t+1)=max(0,(1-rho)tau_ij(t)+delta_tau_ij)` without stating an upper clamp, a replacement or merge rule for repeated emission, or the order of decay against a same-turn deposit. No official artifact and no written lecturer clarification has answered it. `official_status` therefore **stays OPEN**.

**Convention.** Two scent profiles are implemented behind one common interface, recorded in full in `docs/mechanisms/M-01-scent-model.md` §B and selected through `ADR-004`:

- **Default — `subtractive_chebyshev_v1`.** Linear Chebyshev falloff from the emitting cell; emitted values merge into the existing field by maximum per cell, never by addition; deposit first, then decay the whole field; subtractive decay `round(max(0, tau - 0.1), 3)`; rounding to 3 decimal places at both emission and decay; lower clamp at `0.0` with no upper clamp; once per full turn; only cells strictly greater than `0` retained; the field is transmitted and the receiver decays it.
- **Additionally supported — `multiplicative_book_v1`.** The printed 5×5 kernel looked up verbatim by offset; multiplicative decay `(1 - rho) * tau` with `rho = 0.1`; decay first, then deposit; evaluated exactly as `(1 - rho) * tau + delta` then clamped to `[0.0, 0.9]`; no rounding; once per full turn from an empty start; recomputed by each side rather than transmitted.

Edges and corners clip to the board in both profiles: a cell outside the board receives no value, and clipping never wraps, reflects, or redistributes intensity. Exactly one profile is active per pairing, and the active model is declared and compared as a document hash, so a mismatch is refused before play rather than diverging silently mid-game.

**Verification.** Deterministic vectors committed under T005 cover both profiles independently: single emission, repeated emission at the same cell, saturation behavior (no upper clamp under the default profile, clamping at `0.9` under the book-form profile), decay sequences, board edges, board corners, and the model-lock hash. Both role repositories run the same vectors.

**Explicitly not claimed.** Neither profile is the official reading of section 4.3. This convention states what the project builds, never what the source means, and the official question stays open until an official answer is registered and verified. Confirmation of the selected profile happens before counted play.

`implementation_status: OPERATIONAL_CONVENTION`; `latest_safe_resolution_gate: before-counted-play`.

## OPEN-011 termination readings (operational convention for testing only)

The official ambiguity stays open and is not converted into a rule.

**Convention.** Both readings are exercised as explicit differential tests: move cap and survival threshold as one termination event versus two, and one counted move as a full round versus a single half-turn. Neither reading is selected as a production default. A move-cap exhaustion below the survival threshold refuses to score rather than producing a guessed outcome, and a sub-game whose configured `max_moves` and `survival_threshold` diverge refuses to start.

**Counted-play gate.** No counted play may proceed while the two values diverge or while the outcome of a move-cap exhaustion is unresolved.

`implementation_status: DIFFERENTIAL_TESTS_ONLY`; `latest_safe_resolution_gate: before-counted-play`.

## Input gates

Four named classes group the eleven `OPEN-*`/`INPUT-*` items by *when* they become blockers:

| Gate | Class | Covers | Ready when |
|---|---|---|---|
| `G-OFFICIAL` | official artifact intake | INPUT-001…008, INPUT-011; OPEN-001, 002, 004, 005 (label only), 006, 007, 008, 009, 011 | the course supplies the file or the answer |
| `G-PROFILE` | implementation-profile decisions | PLANQ-002…008 | project team decides |
| `G-TEAM` | public team metadata | INPUT-009; OPEN-003 (team part), OPEN-010 | human confirmation |
| `G-LIVE` | live pairing / opponent / endpoints | INPUT-010; OPEN-003 (remainder) | opponent agreed, tunnels up |

## Implementation Decision Register

The following items are project decisions, not official requirements and not substitutes for OPEN-001 through OPEN-011. Resolve them during the relevant task-planning step; the project team approves the value. Record only sufficiently important and durable technical decisions in an ADR. Use a Change Request only for a material change to an approved requirement or PRD contract. Additional implementation work receives a new stable task ID instead of silently expanding an active task.

| ID | Planning question | Constraints / options to examine | Decision | Owner | Affected tasks |
|---|---|---|---|---|---|
| PLANQ-001 | What are the Police and Thief repository URLs, and which confirmed GitHub handle maintains each repository? | The two repository URLs are objectively verifiable from the configured remotes and are recorded. Maintainer assignment is a human fact and is not inferred from commit authorship. | **PARTIALLY RESOLVED (2026-08-16).** Police: `https://github.com/evya1/police_repo`. Thief: `https://github.com/evya1/thief_repo`. Per-repository maintainer ownership among `evya1` and `Us5rName` remains `TBD_TEAM_DECISION`. | project team | T001, T023, T026 |
| PLANQ-002 | Which Python baseline, FastMCP direct-dependency policy, and test/quality dependency baseline form the initial T002 lock under the accepted `uv` policy? | T002 owns only the Python runtime baseline, the FastMCP direct runtime dependency, the existing test/quality dependency baseline, the accepted `uv` policy, and creation plus verification of the *initial* lock. The GUI toolkit belongs to PLANQ-007, the Gmail sender to PLANQ-005, and an optional model provider to PLANQ-003; T002 must not install any of them. `pyproject.toml` and `uv.lock` are repository-global integration artifacts with serialized mutation ownership: a later dependency change is assigned as explicit dependency-integration work, and a component worker never widens its own `write_set` to reach them. | **RESOLVED (2026-08-16).** Python 3.12 is the CI/runtime baseline. The declared runtime range stays `>=3.12` unless actual dependency compatibility forces a narrower range. FastMCP is a direct runtime dependency at `fastmcp>=3.4,<4` — the current stable major line, verified to resolve on Python 3.12 with the declared range; the unreleased 4.x line is excluded until it ships and is evaluated. The current quality/test tooling (`pytest`, `pytest-cov`, `ruff`, `pre-commit`, `pyyaml`) is preserved. `uv` remains the package/dependency manager and is **not** added as an application dependency. No GUI, Gmail, or model-provider dependency is selected here. | project team + orchestrator | T002 |
| PLANQ-003 | Is an external language-model provider needed, and if so which provider/model, call cadence, token/cost budget, and rate limits? | Optional P2 work only. | **RESOLVED (2026-08-24).** Deterministic template mode remains the default legal path. The optional production path uses OpenRouter through a dependency-free standard-library HTTP client, model `inclusionai/ling-3.0-flash`, provider slug `novita`, `OPENROUTER_API_KEY`, optional `OPENROUTER_BASE_URL`, 30-second per-step deadline, 10 output tokens, every eligible step, and the shared Gatekeeper's 30-request-per-minute default with at most one retry. CI uses fake transports and never performs a live call; live evidence remains explicit opt-in. | project team + orchestrator | T013, T017, T027, T050, T051 |
| PLANQ-004 | If a language-model provider is selected, what may it generate? | Must not weaken deterministic legality. | **RESOLVED (2026-08-16).** A model provider may generate only free-form text: verbal hints, natural-language explanations, and post-hoc behavior analysis. It must never determine whether a movement action is legal, select or veto a movement action, reorder candidate actions, or delay a turn in a way that bypasses the deterministic strategy and domain rules. Legality and action selection are computed by the domain and strategy modules alone, and the deterministic template fallback is always available. | project team + orchestrator | T007, T027 |
| PLANQ-005 | Which Gmail sender implementation will satisfy the reporting and security requirements? | Verify send-only `gmail.send`, central Gatekeeper use, exact JSON attachment bytes, idempotency, secret handling, and tests. A draft creator or pretty-printed message-body substitute is noncompliant for counted reporting. | **RESOLVED (2026-08-20).** Send-only Gmail adapter (`GmailSender`) implementing mandatory `gmail.send` scope verification, client injection behind central `ExternalApiGatekeeper` (token bucket, DoS lockout, 429 backoff, non-retryable exception handling), draft-substitution refusal (`DraftSubstitutionError`), duplicate send prevention, exact JSON attachment bundling (`ReportingArtifactBundle`), and explicit recipient configuration without hard-coded unofficial fallback. Live transmission gated behind human G-LIVE approval. | project team + orchestrator | T017, T018 |
| PLANQ-006 | Which public endpoint/tunnel procedure and test opponent will be used? | Must preserve two independent processes, approved shared terms, and a human gate before counted play. These are live values: an opponent identity, an endpoint, a tunnel URL, and connectivity evidence are recorded only once they are real. | `TBD_TEAM_DECISION` — collection in progress. Required inputs: opponent team identity; each side's public MCP endpoint; the tunnel procedure and its restart behavior; captured connectivity evidence for a successful two-peer handshake. None is a blocker for local implementation, which runs two local processes with no endpoint. | project team | T009, T020, T022 |
| PLANQ-007 | Which GUI toolkit and evidence-capture workflow will be used? | Must show local truth plus belief only, keep Replay immutable, and capture real—not fabricated—submission evidence. | **RESOLVED (2026-08-23).** Toolkit: **standard-library `tkinter`**. No GUI package is added to `pyproject.toml` or `uv.lock`, so PLANQ-002's dependency baseline is unchanged and the GUI cannot become an install-time failure for a grader. Rationale: the lecturer requires a *runnable* Live GUI and Replay Viewer, and the lowest-risk way to guarantee that on an unknown marking machine is to depend on nothing. The view models are pure and tested headlessly; only the thin adapter imports `tkinter`, so the whole view layer stays testable without a display. Evidence-capture workflow: run the viewer against a genuinely generated bundle under a real display (Xvfb where no desktop exists) and screenshot the actual window — one honest bundle showing green `Verified OK`, one tampered copy of that same bundle showing red `TAMPERED`. Screenshots are never mocked, composed, or produced by a headless CLI. | project team + orchestrator | T014, T015, T023 |
| PLANQ-008 | Which role-specific heuristic priorities and seeded scenarios will be approved? | Police and Thief strategies remain separate; choices must satisfy legal-action, hint, belief, and audit constraints. | Resolved as a **team design decision** (not an official rule) — see `docs/decisions/ADR-006-strategy-heuristic-priorities.md` for the approved priority orderings and required seeded negative controls (always-STAY, disconnected-belief). Superseded if a binding/official spec is later found to conflict. | project team + orchestrator | T007, T021, T037, T038 |

## Resolution rule

An official-input question closes only after the file or answer is registered and verified, private values remain outside published artifacts, affected IDs are named, and the orchestrator reconciles the necessary derived artifacts. If the input fills an existing contract without changing approved normative meaning, no Change Request is opened. If it materially changes an approved requirement or PRD contract, use an approved Change Request and resulting PRD version. A durable technical choice may use an ADR; newly discovered implementation work receives a new task. Silence, sample code, or a convenience draft is not resolution.

Recording an operational convention is never an official closure and never changes `official_status`. A convention states what the project builds and how that is verified; it never states what the source means. When an authoritative answer arrives that contradicts a convention, the convention is replaced and its adapter boundary absorbs the change.
