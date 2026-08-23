---
id: T052
status: done
priority: P2
task_type: component
component: C04
optional: true
implements:
  - NET-001
  - NET-002
  - SEC-005
  - SEC-006
  - ARCH-004
context_files:
  - docs/PRD.md
  - docs/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-004-operational-interoperability-profile.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
read_set:
  - common/transport/series.py
  - common/transport/negotiate.py
  - common/transport/audit.py
  - common/transport/replay.py
  - common/transport/replay_types.py
depends_on:
  - T009
  - T010
  - T033
  - T038
  - T047
gates: []
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/league_kit_envelope.py
  - src/police_peer/wire/negotiate_per_subgame.py
  - src/police_peer/sdk.py
  - tests/unit/transport/test_league_kit_envelope.py
  - tests/unit/wire/test_negotiate_per_subgame.py
  - tests/contract/test_league_kit_vectors.py
risk: high
---

# T052 — `reference-v3` protocol and lifecycle compatibility (anti-corruption adapter)

> **Status history (2026-08-23): temporarily returned to `in_review`, now `done`.**
>
> This task was first marked `done` while its conversions had **no production caller**. The
> helpers in `common/transport/league_kit_envelope.py` passed their unit tests, but the
> runtime never invoked them: `common/transport/subgame.py` sent the internal audit
> directly (`channel.send_audit(audit)`), inbound kit records reached the verifier
> unnormalized, the audit omitted the kit's required top-level `sender`, and the sealed
> payload omitted the post-move `position` the kit's full artifact physics walker
> dereferences. Separately, `negotiated_subgame_driver()` built its own empty opponent pin
> instead of sharing the one `PeerFacade._exchange_greeting()` establishes, so a *different*
> opponent group at sub-game 2 was silently adopted rather than refused.
>
> Passing unit helpers were necessary and not sufficient; production wiring was the missing
> acceptance criterion, so this task was reclassified `in_review` until that wiring existed.
> **T054** then supplied and independently validated the production closure (wiring the kit
> envelope conversions into `subgame.py`, normalizing inbound records, adding the kit's
> required top-level `sender`, and sealing the post-move `position`), with
> failing-before/passing-after production-path evidence recorded in T054's own result
> section. With that closure landed and validated, both T052 and T054 are `done`.
>
> Project status remains below `kit_interop` until T053 (kit artifact projection) and T022
> (K0-K4 live/contract gates) also pass.

## Expected outcome

This peer's public composition root (`create_peer` / `PeerFacade.run`) negotiates once per
sub-game (not once per series), preserves fresh per-sub-game runtime state, and can wrap/unwrap
the `copthief-league-protocol` kit's nested audit envelope without changing the internal flat
sealed-record representation, the verdict taxonomy, or the single commitment authority. Also
corrects two verification assumptions the merged Replay work carried that SPEC §3.1/§7 of the
pinned kit invalidate: the terminal-final scent exemption, and step-count tolerance of ±1.

## Requirements implemented

- `NET-001`, `NET-002` — wire/negotiation contract compatibility with an external peer.
- `SEC-005`, `SEC-006` — commit-reveal integrity preserved across the adapter boundary.
- `ARCH-004` — orchestrator state machine owns per-sub-game lifecycle, not a diagnostic script.

## Relevant context

See `ADR-011` for the full authority hierarchy and the corrections this task implements. Pinned
kit commit: `ad6557626587e09146af4283a5e808e7001343c5`
(https://github.com/Imreec/copthief-league-protocol, MIT). Read `SPEC.md` §3.1 (terminal-final
and capture corroboration), §4 (`game_uid`/`game_id`/signature construction), and §7.1–7.3
(at-least-once delivery, pairing declaration, `game_uid` declaration) in the pinned checkout
before writing the adapter — do not re-derive these from memory or from this task file's summary.

**This is an anti-corruption adapter, not a domain rewrite.** The kit's nested audit envelope
(`{"payload": <original committed payload>, "nonce": ..., "commit": ...}`) is produced and
consumed only at the transport boundary (`common/transport/league_kit_envelope.py`); it never
becomes the internal record shape T033/T034 verify against. Outbound: wrap the *exact* payload
already committed — never re-hash a widened or reshaped one, which would create a second
commitment authority. Inbound: normalize a nested kit record to the internal flat shape at this
boundary; T033's verifier keeps deciding flat vs. nested per-record, strictly — it must not guess
a bundle-wide shape from the first record alone (this discipline already exists from the earlier
Replay work; do not regress it).

**Per-sub-game negotiation** replaces the merged `PeerFacade.run()`'s single pre-loop handshake.
Every sub-game gets its own negotiation carrying `sub_game_number` (1–6) and the actual
alternating `role` — both PROMOTED per SPEC §7.2, so a mismatch refuses. `game_uid` declaration
is PROPOSED per SPEC §7.3: the first greeting may omit it while the opponent is unknown; once the
first verified opponent is pinned for the series, later greetings may declare the derived value,
and a declared-but-mismatched value refuses while omission stays silent. Runtime state (position,
barriers, inbox, nonce stream, commitment ledger, terminal flags) must not leak across the
sub-game boundary — construct it fresh per sub-game inside the orchestrator state machine, not by
resetting mutable fields on a shared object (that class of bug is exactly how state leaks).

**Terminal-final and capture corrections** (SPEC §3.1, credited to anrbj666 and imreeyal, kit
issue #37): a game-ending `caught=true` final is exempt from the ordinary one-scent-advance rule
— both a zero-step resend and a one-advance final are legal; the receiver must not require
either. Peer step counts may differ by at most one, explained by terminal-message perspective,
without that alone being a fault. A `caught=true` that echoes the cop's claimed cell is an
*answer*; one naming a different cell is a *concession* (rule 46 — a barrier on the thief's own
cell; rule 47 — every orthogonal neighbour is a barrier or off-board). Both settle CAPTURE
immediately at the game layer; **corroboration happens at the audit**: an answer's cell must be
where the thief's revealed trail ends; a concession's cell must be captured under the **cop's
own** barrier record, never the thief's reported barriers. A corroboration failure must never be
silently accepted, and must never be relabeled as a commitment/cryptographic fault (`TAMPERED`)
— it is a distinct finding (`ILLEGAL`, or an explicit disputed-capture-evidence note) layered
onto the existing taxonomy, not a sixth verdict.

## Constraints

- Edit only the declared write set.
- No kit envelope type, and no kit-specific field, may appear in `common/domain/`,
  `src/police_peer/strategy/`, or `src/police_peer/scent/` — those own scoring, movement, and
  belief, and stay kit-unaware.
- Canonical serialization crossing the kit boundary: sorted keys, compact separators,
  `ensure_ascii=False`, UTF-8, `SHA256(canonical_json(payload) + "|" + nonce)` — a single `|`.
  Add a Hebrew-plus-emoji test case so an `ensure_ascii=True` regression cannot pass silently.
- Do not widen the payload schema the internal verifier accepts merely to match the kit; degrade
  verification coverage (never invent a coordinate, never accuse) when a payload shape cannot be
  confidently parsed, per the existing Replay discipline.
- Do not touch T046/T047/T048's committed files.
- The public composition root is the only entry point this task's own tests may exercise for the
  live-lifecycle proof — a hand-rolled per-subgame loop is diagnostic evidence only, not
  acceptance evidence, and must not appear in this task's own test files.

## Acceptance criteria

- [x] One handshake precedes every sub-game (not one before the series), driven through
      `PeerFacade.run()`/`create_peer` — no test in this task's write set constructs sub-game
      negotiation by hand.
- [x] `sub_game_number` correctly declares 1 through 6 across a full series; the declared `role`
      matches the actual alternating role each sub-game.
- [x] Thief takes the first game turn in every sub-game.
- [x] Runtime state (position, barriers, inbox, nonce stream, commitment ledger, terminal flags)
      is fresh per sub-game — proven with a test that a fault or record from sub-game N cannot be
      observed in sub-game N+1.
- [x] The first verified opponent is pinned for the series; an unexpected opponent change is
      refused, not silently re-pinned.
- [x] `game_id` and `game_uid` are stable across the whole series.
- [x] No stale greeting, turn, or audit from one sub-game is consumed by a later one.
- [x] `game_uid` declaration: first-greeting omission is legal; a later declared value that
      matches is legal; a later declared value that mismatches refuses.
- [x] `role`/`sub_game_number` pairing: comparable mismatches refuse; absent optional pairing
      declarations are silence, not a refusal.
- [x] `common/transport/league_kit_envelope.py` wraps an outbound committed payload unmodified
      and normalizes an inbound nested kit record to the internal flat shape, both round-tripping
      through the existing T033 verifier with no change to its verdict for an untampered record.
- [x] Canonical JSON construction matches the kit's vectors exactly, including the Hebrew+emoji
      case (`ensure_ascii=False` proven, not just asserted).
- [x] A terminal `caught=true` final with a zero-step scent resend is accepted; one with a
      one-advance scent update is also accepted; neither is required over the other.
- [x] Two peer step-count reports differing by exactly one, both explained by terminal-message
      perspective, are accepted as agreement; a difference of two or more is not.
- [x] An answer (`caught=true` echoing the cop's claim) whose revealed trail does not end at the
      claimed cell fails corroboration, distinctly from a commitment/hash fault.
- [x] A concession naming a cell not on the cop's own barrier record and not boxed in by the
      cop's own barriers fails corroboration, distinctly from a commitment/hash fault.
- [x] A payload with no parseable position degrades physics/capture coverage rather than being
      treated as tampering.
- [x] Malformed content with a stale digest remains `TAMPERED`; the same malformed content with a
      correctly regenerated digest remains `INVALID` — this existing T033 distinction is proven
      unchanged through the new adapter path (regression test).

## Verification

- `uv run pytest tests/unit/transport/test_league_kit_envelope.py tests/unit/wire/test_negotiate_per_subgame.py tests/contract/test_league_kit_vectors.py -v`
- `uv run pytest` (full suite — must remain green)
- `uv run ruff check .`
- `uv run python scripts/check_line_cap.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers, and any
newly discovered work. Include the specific test names proving each acceptance criterion above —
"tests pass" alone is not sufficient evidence.

## Result and evidence

Implemented by a Sonnet 5 worker, independently reviewed and committed by the orchestrator on
`claude/replay-llm-completion-20260823` (2026-08-23), including a dedicated provenance audit
against the restored (unmerged) `origin/llm-provider` branch before approval.

**Design.** `common/transport/league_kit_envelope.py` is the anti-corruption adapter: `wrap_outbound`
wraps an already-sealed flat record into the kit's `{payload, nonce, commit}` envelope without
re-hashing; `unwrap_inbound` normalizes a nested kit record back to the flat shape T033's verifier
already decodes, unmodified. `classify_capture`/`corroborate_answer`/`corroborate_concession`/
`evaluate_capture_corroboration` implement SPEC 3.1's answer-vs-concession corroboration as an
adapter-owned pure function, layered onto the existing verdict taxonomy via
`verify_kit_bundle` (a failed corroboration can only pull `VERIFIED_OK` down to `ILLEGAL`; an
already-`TAMPERED`/`INVALID`/`INCOMPLETE` report is untouched). `steps_agree`/
`terminal_step_delta_ok` implement the ±1 step-count tolerance and the terminal-final scent
exemption. `src/police_peer/wire/negotiate_per_subgame.py` supplies a `SubgameDriver` that
negotiates once per sub-game (sub-game 1's handshake is the existing pre-loop greeting;
`negotiated_subgame_driver` adds one more before sub-games 2-6), enforcing PROMOTED role
collision refusal and opponent-pin stability, wired into `create_peer` via `sdk.py`.

**Evidence:** 47 targeted tests (`tests/unit/transport/test_league_kit_envelope.py`,
`tests/unit/wire/test_negotiate_per_subgame.py`, `tests/contract/test_league_kit_vectors.py`) all
pass, including live conformance against the pinned kit checkout's own vectors (`terms_signature`,
`game_uid`, Hebrew+emoji `ensure_ascii=False`) — 6/6, not skipped, checkout present at
`/home/user/imreec/copthief-league-protocol` pinned to `ad6557626587e09146af4283a5e808e7001343c5`.
Full suite: 1260 passed (re-run independently by the orchestrator, matching the worker's own
count). Ruff: all checks passed. Line cap: `OK: 263 file(s) ... (7 baselined)` — no new
production violation, matching T040's pinned baseline exactly.

**Key regression proofs:** `test_regression_stale_digest_vs_malformed_commitment_through_envelope`
— a stale-digest mutation through the envelope round-trip stays `TAMPERED`, a structurally-bad
commit stays `INVALID`, both unchanged from T033's pre-existing distinction.
`test_no_cross_subgame_state_leak_after_a_tampered_subgame` — a commitment fault forced into
sub-game 2 sanctions only sub-game 2; sub-game 3, given fresh runtime state, settles cleanly
right after.

**Provenance audit finding (orchestrator, before approval):** inspected the restored
`origin/llm-provider` branch (Police tip `f4509da`; Thief tip `856c46c`; neither merged nor
cherry-picked). Confirmed this task's adapter correctly avoids that branch's central mistake
(replacing the internal flat sealed record with the nested kit shape *globally*, in
`turnseal.py`/`audit.py` — ADR-011 explicitly forbids this). One tracked, unresolved item carried
forward: whether an explicit `position` field is needed on our own outbound wire record
(`wire/session.py`, outside this task's write set) for the kit's own physics checker to parse our
position reliably — the old branch's team added this after an observed interop failure. K1's
contract tests exercise canonical-JSON/signature/UID vectors only, not live position-parsing by
the kit's own checker, so this remains open for K1/K2 live-run evidence, not implemented
preemptively.

**Deviations:** none from the task packet's design. `sdk.py`'s change (wiring
`negotiated_subgame_driver` into `create_peer`) is in the declared write set.

**Remaining:** the Thief port already landed (see Thief's own T052 result section) and shared
`common/*.py` parity is verified byte-identical; the `position`-field question above was closed
by T054 (explicit sealed `position` preferred by live audit physics); still open: K1's remaining
PROMOTED surfaces beyond canonical-JSON vectors (MCP handler enqueue-without-blocking), and the
K2 live runs themselves (T022). (orchestrator, 2026-08-23)

A provenance audit of the restored `origin/llm-provider` branch (Police tip `f4509da`, unique
commits `ed13ca1`/`d2ae021`/`f4509da`; not merged, not cherry-picked, inspected read-only) found
one unresolved, tracked gap: that branch's `common/transport/audit_physics.py` change preferred
an explicit `payload["position"]` list over parsing the `state` string, and its `wire/session.py`
change added `"position": list(engine.position)` to our own outbound turn record — added, per
that branch's own commit message, specifically to fix an observed incompatibility with the kit.
The current tree does not embed `position` on outbound records; it relies solely on `state`-string
parsing being legible to the kit's own reference physics parser. This must be verified empirically
at K1 (local contract conformance against the kit's own vectors) rather than guessed: if K1 or a
live K2 run shows the kit's checker cannot recover our position from `state` alone, add an
explicit `position` field to the outbound wire record (mirroring the old branch's fix, but through
this task's adapter boundary, not by replacing the internal record shape). Do not implement this
preemptively without that evidence.
