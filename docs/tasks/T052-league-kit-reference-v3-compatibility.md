---
id: T052
status: not_started
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

- [ ] One handshake precedes every sub-game (not one before the series), driven through
      `PeerFacade.run()`/`create_peer` — no test in this task's write set constructs sub-game
      negotiation by hand.
- [ ] `sub_game_number` correctly declares 1 through 6 across a full series; the declared `role`
      matches the actual alternating role each sub-game.
- [ ] Thief takes the first game turn in every sub-game.
- [ ] Runtime state (position, barriers, inbox, nonce stream, commitment ledger, terminal flags)
      is fresh per sub-game — proven with a test that a fault or record from sub-game N cannot be
      observed in sub-game N+1.
- [ ] The first verified opponent is pinned for the series; an unexpected opponent change is
      refused, not silently re-pinned.
- [ ] `game_id` and `game_uid` are stable across the whole series.
- [ ] No stale greeting, turn, or audit from one sub-game is consumed by a later one.
- [ ] `game_uid` declaration: first-greeting omission is legal; a later declared value that
      matches is legal; a later declared value that mismatches refuses.
- [ ] `role`/`sub_game_number` pairing: comparable mismatches refuse; absent optional pairing
      declarations are silence, not a refusal.
- [ ] `common/transport/league_kit_envelope.py` wraps an outbound committed payload unmodified
      and normalizes an inbound nested kit record to the internal flat shape, both round-tripping
      through the existing T033 verifier with no change to its verdict for an untampered record.
- [ ] Canonical JSON construction matches the kit's vectors exactly, including the Hebrew+emoji
      case (`ensure_ascii=False` proven, not just asserted).
- [ ] A terminal `caught=true` final with a zero-step scent resend is accepted; one with a
      one-advance scent update is also accepted; neither is required over the other.
- [ ] Two peer step-count reports differing by exactly one, both explained by terminal-message
      perspective, are accepted as agreement; a difference of two or more is not.
- [ ] An answer (`caught=true` echoing the cop's claim) whose revealed trail does not end at the
      claimed cell fails corroboration, distinctly from a commitment/hash fault.
- [ ] A concession naming a cell not on the cop's own barrier record and not boxed in by the
      cop's own barriers fails corroboration, distinctly from a commitment/hash fault.
- [ ] A payload with no parseable position degrades physics/capture coverage rather than being
      treated as tampering.
- [ ] Malformed content with a stale digest remains `TAMPERED`; the same malformed content with a
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

(to be filled)
