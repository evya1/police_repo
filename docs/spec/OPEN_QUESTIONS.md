# Open Questions and Missing Official Inputs

These are active blockers and confirmations, not permission to guess. T001 records an arriving authoritative input in `INPUT_REGISTER.md`, verifies it, updates the affected `OPEN-*` entries, and reconciles derived artifacts. Input receipt does not create a Change Request unless accepting the information changes an already-approved canonical product requirement or PRD contract.

## Two independent axes

`official_status` records whether the course/lecturer has actually closed the question. Only a verified official answer moves it to `RESOLVED`. `implementation_status` records how much local work can proceed without that answer. The two are independent: an item can remain `official_status: OPEN` while its `implementation_status` narrows to a specific, named criterion instead of blocking an entire task.

`implementation_status` values:

- `RESOLVED_LOCALLY` — the authoritative material already fully determines every implementable behavior; no task waits on this item.
- `DIFFERENTIAL_TESTS_ONLY` — implementation proceeds using the compatibility-matrix pattern (candidate behaviors compared, none selected as production default); only the final lock/selection criterion waits.
- `DRAFT_CONTRACT_NONOFFICIAL` — an internal, explicitly-labeled-non-official contract may be built and used locally; only cross-peer byte agreement waits.
- `LATE_RUNTIME_INPUT` — the input is expected only late in the project lifecycle (team confirmation, opponent, submission form); it does not block early work.
- `HARD_BLOCK` — no local work may substitute for the missing answer at the named scope.

`latest_safe_resolution_gate` names the acceptance criterion or integration gate (see `docs/tasks/T###` `gates:` entries and `planning/INTEGRATION_PLAN.md`) beyond which the item must be resolved. `blocks` / `does_not_block` state the scope precisely, replacing a flat "this open item blocks this task" reading.

## Active OPEN items

| ID | Type | Question / missing input | Impact | Required next action | Owner |
|---|---|---|---|---|---|
| OPEN-001 | MISSING OFFICIAL INPUT | The four official attached JSON templates/schemas and their exact canonical rules were not supplied. Runtime instances are expected to be produced during the lifecycle: declaration before the series, configuration before each sub-game, log during/finalized after each sub-game, and result after verified series settlement. | Blocks T016, reporting integration, and final cross-team artifact verification; it does not imply that completed match instances should already exist. | Obtain the original declaration, configuration, log, and result templates/schemas from Moodle; do not synthesize their field contract or canonical bytes. Flat and nested candidate layouts with differing field sets may be retained only as test cases showing why a substitute is unsafe. | orchestrator + project team/lecturer |
| OPEN-002 | MISSING OFFICIAL INPUT | The official Moodle Word-to-PDF submission template was not supplied. | Blocks the final Moodle submission packet in T026. | Download the exact template and fill it without moving or changing fields. | orchestrator + project team/lecturer |
| OPEN-003 | TEAM INPUT | Confirmed non-secret metadata: team name `ZeroOne`, team number `01`, and GitHub handles `evya1` and `Us5rName`. Still unknown: the valid eight-character final-project group code, role repository URLs, public MCP endpoints, opponent values, and any private identity fields required only by an official submission form. | Blocks live endpoints, counted play, final reporting identifiers/links, and submission, but not repository planning. | Retain the confirmed public metadata; replace the remaining placeholders only after team/lecturer confirmation. Do not infer the eight-character code from a previous submission label, and never add government IDs to repository artifacts. | orchestrator + project team/lecturer |
| OPEN-004 | SOURCE CONTRADICTION | §9.3.3 says the non-reporting side receives no credit, while Appendix E rule 35 says a missing or conflicting report invalidates the game and gives both sides 0. | Blocks final report-refusal/sanction behavior and T018 settlement. | Ask the lecturer which sanction governs; until then require two consistent reports and block automatic scoring of the conflict. | orchestrator + project team/lecturer |
| OPEN-005 | SOURCE AMBIGUITY | The Minimum status for operational maxima such as requests_per_minute or concurrent_requests does not unambiguously define the 'harder' direction. **Reclassified — see "OPEN-005 reclassification" below; official_status remains OPEN.** | Narrowed: blocks only labeling/approving a proposed negotiated change to an operational Minimum parameter. Does not block CFG-005/CFG-007 validation, default-value operation, the Game Core configuration boundary (T003), or C04 retry/timeout behavior (T011, T017). | Use printed defaults unless both teams document an agreement; obtain lecturer guidance before labeling a change as "harder" or "easier". | orchestrator + project team/lecturer |
| OPEN-006 | MISSING OFFICIAL INPUT | Whether Step 0 requires any additional course-supplied credential beyond the documented declaration/commitment/integrity mechanism (M-05) is unconfirmed; no authoritative material establishes that a course-supplied signing credential exists. | Blocks final confirmation of the Step 0 signing procedure and counted play. | Ask the lecturer whether a course-supplied credential is required for Step 0 beyond the project's own commit-reveal integrity mechanism; do not invent or commit keys. Locally generated Nonces, hashes, or example signature fields do not answer the question either way. | orchestrator + project team/lecturer |
| OPEN-007 | SCHEMA AMBIGUITY | The book binds at least State/Move/Intent/Nonce but mentions a richer record; nonce placement, Unicode escaping, canonical separators, report-consensus signature scope/form, and the game_uid/game_id relationship depend on missing official files. | Blocks cross-peer canonical hash fixtures and final integrity/report envelopes; does not block local Commit-Reveal primitives built against the internal draft contract (`docs/mechanisms/M-05-commit-reveal-integrity.md`, `docs/contracts/CT-04-canonical-bytes.md`). | Implement only after OPEN-001 is resolved; meanwhile define an internal draft contract explicitly labeled non-official. Test compact versus spaced JSON, nonce-inside versus nonce-appended constructions, Unicode/float behavior, and sign-then-insert scope without selecting any as official. | orchestrator + project team/lecturer |
| OPEN-008 | TERMINOLOGY / SERIES SEMANTICS | The terms game, match, series, and sub-game overlap; Appendix F fixes six sub-games but does not state role assignment/alternation, and the cumulative-tie wording does not unambiguously say whether the score of 2 replaces or is added to accumulated points. | Blocks exact role schedule, aggregation labels, tie settlement, and report fields but not the binding count of six or tie value 2; series mechanics (T019) may be built and tested against the fixed GAME-013 score table. | Confirm these semantics from the official reporting files or lecturer before counted play; retain the binding numeric values. Series-add, series-replace, and per-sub-game tie handling are test candidates, not approved defaults. | orchestrator + project team/lecturer |
| OPEN-009 | SOURCE AMBIGUITY | Section 4.3 states that scent intensity is in `[0, 0.9]` and gives `tau_ij(t+1)=max(0,(1-rho)tau_ij(t)+delta_tau_ij)`. Repeated emission can exceed 0.9, but no upper clamp, replacement, or merge rule is stated. **Reclassified by an operational convention — see "OPEN-009 reclassification" below; official_status remains OPEN.** | Narrowed: blocks only the claim that any implemented profile is the *officially correct* reading of section 4.3, and the confirmation step required before counted play. Does not block implementing scent (T005), selecting the default scent profile, generating or declaring the selected model lock, or local testing. | Obtain lecturer confirmation of saturation/merge and update order; record a numeric repeated-emission example and confirm the approved model before counted play. Until then implement the profiles named in `ADR-004`, keep both registered models supported and vector-tested, and never label either as the official reading. | orchestrator + project team/lecturer |
| OPEN-010 | HUMAN CONFIRMATION | Confirm the public team metadata and GitHub handles. | Blocks counted play and final submission; it does not block local planning or implementation. | Verify the recorded team name `ZeroOne`, team number `01`, and GitHub handles `evya1` and `Us5rName` against a human-approved team record before counted play and final submission. Preserve the values until confirmation; do not guess replacements or add private identity data. | project team |
| OPEN-011 | SOURCE AMBIGUITY | GAME-014 fixes a move cap and a survival threshold that both default to 35, but no source states whether they are one termination event or two, which outcome and score a move-cap exhaustion produces, or whether one counted move is a full round in which both sides act or a single half-turn. | Blocks the terminal-outcome map, sub-game settlement, and any counted play whose two values diverge; the binding minimum of 35 for each value and the GAME-013 score table are unaffected. | Ask the lecturer whether reaching the move cap yields the GAME-013 survival score or a technical loss, and whether the count is per round or per half-turn. Until then treat cap-versus-threshold ordering and round-versus-half-turn counting as differential tests only, and refuse to start a sub-game whose two values diverge rather than guessing a precedence. | orchestrator + project team/lecturer |

## OPEN-005 reclassification (dated 2026-08-15)

**Evidence re-examined.** `CFG-005` (Appendix E rule 12; Appendix F status definitions; PDF p. 144, 151, 155) states, verbatim: *"A Fixed value is immutable; a Negotiated value may be freely agreed and defaults when no agreement exists; a Minimum value cannot fall below its threshold and may be made harder only by agreement."* This is corroborated verbatim in `final_project_requirements_en.md:192` and `:402` ("`Minimum` is a floor that may not be weakened"), and in the Hebrew audit register row `AUD-052`.

**Finding.** This authoritative text establishes two independently enforceable rules that together fully determine every implementable behavior for the nine `CFG-007` Minimum parameters: (1) an absolute floor — a configured value below the printed threshold is rejected unconditionally, with no agreement able to weaken it; (2) an agreement precondition — any deviation from the printed default requires recorded mutual agreement. Under these two rules, configuration validation and every runtime default are fully specified without knowing which direction "harder" points. Since rule 2 already requires agreement for a change in either direction, the missing directional label changes no enforceable behavior.

**What remains genuinely open:** only the semantic label itself — whether "harder" is stated for descriptive clarity in a future negotiation record, not whether a change is legal. `official_status` therefore **stays OPEN**; the authoritative material does not define the directional semantics, and this reference-material analysis does not close an official question. Supporting/reference material alone must not close it, and none is treated as doing so here.

**Resolution applied:** `implementation_status` moves from an effective task-level blocker to `RESOLVED_LOCALLY`; `latest_safe_resolution_gate` is set to `before-negotiated-change-to-a-Minimum-parameter`; `blocks` is narrowed to labeling/approving such a proposed change. The original question text, ID, owner, and required next action above are unchanged — this note is additive.

## OPEN-009 reclassification (operational convention, dated 2026-08-16)

**What did not change.** The official question is untouched. Section 4.3 still states an
intensity range of `[0, 0.9]` and the recurrence `tau_ij(t+1)=max(0,(1-rho)tau_ij(t)+delta_tau_ij)`
without stating an upper clamp, a replacement or merge rule for repeated emission, or the
order of decay against a same-turn deposit. No official Moodle artifact and no written
lecturer clarification has answered it. `official_status` therefore **stays OPEN**.

**Finding.** Nothing in the available authoritative material settles the repeated-emission,
saturation, or update-order behavior. Deterministic peer agreement still requires each peer to
compute byte-identical scent arithmetic from a shared, pinned definition, so the project needs
two fully specified, independently reproducible profiles — enough to build, test, and declare a
model without guessing, and enough for a peer to detect a profile mismatch before play rather
than diverging silently mid-game.

**Human-approved engineering decision.** The project team has selected
`subtractive_chebyshev_v1` as the default scent profile and `multiplicative_book_v1` as the
additionally supported book-oriented profile, recorded as an operational convention in `ADR-004`
in each role repository (`docs/decisions/`). That is an engineering choice about what the project
builds, not a reading of the book.

**Explicitly not claimed.** This reclassification does not state that OPEN-009 was resolved, that
a lecturer clarified it, or that the official model is subtractive. None of those statements is
permitted anywhere in project artifacts.

**Resolution applied.** `implementation_status` moves from an effective blocker on the model lock
to `DRAFT_CONTRACT_NONOFFICIAL` — the ADR profile is the internal, explicitly-labeled-non-official
contract that implementation, default selection, model-lock generation and declaration, and local
testing may all proceed against.
`latest_safe_resolution_gate` is set to `before-counted-play`. `blocks` narrows to the claim of
official correctness and to that pre-counted-play confirmation; `does_not_block` now covers T005
implementation in full, including the `{#model_lock}` criterion. The original question text, ID,
owner, and impact class are otherwise unchanged; this note is additive, and follows the same
pattern as the OPEN-005 reclassification above.

## Input gates

Four named classes group the eleven `OPEN-*`/`INPUT-*` items by *when* they become ready, so tasks can cite a scope rather than depending on all of T001. Defined once here; referenced by `id` in task frontmatter `gates:` entries.

| Gate | Class | Covers | Ready when |
|---|---|---|---|
| `G-OFFICIAL` | official artifact intake | INPUT-001…008, INPUT-011; OPEN-001, 002, 004, 005 (label only), 006, 007, 008, 009, 011 | Moodle/lecturer supplies the file or the answer |
| `G-PROFILE` | implementation-profile decisions | PLANQ-002…008 | project team decides |
| `G-TEAM` | public team metadata | INPUT-009; OPEN-003 (public part), OPEN-010 | human confirmation |
| `G-LIVE` | live pairing / opponent / endpoints | INPUT-010; OPEN-003 (remainder) | opponent agreed, tunnels up |

## Implementation Decision Register

The following items are implementation-planning decisions, not official requirements and not substitutes for OPEN-001 through OPEN-010. Resolve them during the relevant task-planning step; the project team approves the value. Record only sufficiently important and durable technical decisions in an ADR. Use a Change Request only for a material change to an approved requirement or PRD contract. Additional implementation work receives a new stable task ID instead of silently expanding an active task.

| ID | Planning question | Constraints / options to examine | Decision | Owner | Affected tasks |
|---|---|---|---|---|---|
| PLANQ-001 | What are the final Police and Thief repository URLs, and which confirmed GitHub handle maintains each repository? | Use `evya1` and `Us5rName`; do not infer role ownership or create URLs until the team confirms them. | `TBD_TEAM_DECISION` | project team | T001, T023, T026 |
| PLANQ-002 | Which Python baseline, FastMCP direct-dependency policy, and existing test/quality dependency baseline will form the initial T002 lock under the accepted `uv` bootstrap/version policy? | Start from official capabilities and select the smallest supported set. T002 owns the Python baseline, the FastMCP direct dependency selection, the existing test/quality dependency baseline, the already-approved `uv` bootstrap/version policy, and creation plus verification of the *initial* `uv.lock`. GUI toolkit and dependency choice belongs to PLANQ-007; Gmail sender and dependency choice belongs to PLANQ-005; T002 must not install speculative GUI or Gmail dependencies. `pyproject.toml` and `uv.lock` are repository-global, whole-environment integration artifacts and therefore carry serialized mutation ownership: if a later human-approved implementation decision requires changing project dependencies, the orchestrator must explicitly assign that dependency-file mutation as serialized dependency-integration work before `pyproject.toml` or `uv.lock` is edited, and a component worker must not silently widen its own `write_set` to reach them. If that later integration constitutes new implementation work, it receives a new stable task ID at that time. The T002 lock is accordingly complete for the dependency decisions approved at T002 time rather than the final dependency set of the finished project. | `TBD_TEAM_DECISION` | project team + orchestrator | T002 |
| PLANQ-003 | Is an external language-model provider needed for this implementation mode, and if so which provider/model, call cadence, token/cost budget, and rate limits will be selected? | Optional P2 work only; template mode remains valid, and no live external call occurs before the team approves the provider/model and budget. | `TBD_TEAM_DECISION` | project team | T013, T017, T027 |
| PLANQ-004 | If a language-model provider is selected, what may it generate? | Limit the default integration to free-form verbal hints or behavior analysis; it must not select, veto, delay, or mutate a legal movement action. Deterministic template fallback remains available. | `TBD_TEAM_DECISION` | project team + orchestrator | T007, T027 |
| PLANQ-005 | Which Gmail sender implementation will satisfy the reporting and security requirements? | Verify send-only `gmail.send`, central Gatekeeper use, exact JSON attachment bytes, idempotency, secret handling, and tests. A draft creator or pretty-printed message-body substitute is noncompliant for counted reporting. | `TBD_TEAM_DECISION` | project team + orchestrator | T017, T018 |
| PLANQ-006 | Which public endpoint/tunnel procedure and test opponent will be used? | Must preserve two independent processes, approved shared terms, and a human gate before counted play. | `TBD_TEAM_DECISION` | project team | T009, T020, T022 |
| PLANQ-007 | Which GUI toolkit and evidence-capture workflow will be used? | Must show local truth plus belief only, keep Replay immutable, and capture real—not fabricated—submission evidence. | `TBD_TEAM_DECISION` | project team | T014, T015, T023 |
| PLANQ-008 | Which role-specific heuristic priorities and seeded scenarios will be approved? | Police and Thief strategies remain separate; choices must satisfy legal-action, hint, belief, and audit constraints. | `TBD_TEAM_DECISION` | project team + orchestrator | T007, T021 |

## Resolution rule

An official-input question closes only after the file or answer is registered and verified, private values remain outside public artifacts, affected IDs are named, and the orchestrator reconciles the necessary derived artifacts. If the input fills an existing contract without changing approved normative meaning, no Change Request is opened. If it materially changes an approved requirement or PRD contract, use an approved Change Request and resulting PRD version. A durable technical choice may use an ADR; newly discovered implementation work receives a new task. Silence, sample code, or a convenience draft is not resolution. A reclassification of `implementation_status` performed with cited authoritative evidence (as with OPEN-005 above) is not an official closure and does not change `official_status`. Neither is a reclassification performed on the strength of an approved implementation-profile decision plus non-authoritative interoperability evidence (as with OPEN-009 above): it states what we may build, never what the source means, and the official question stays open until an official answer is registered and verified.
