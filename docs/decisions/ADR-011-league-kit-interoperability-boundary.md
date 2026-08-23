---
artifact: adr
id: ADR-011
status: accepted
date: 2026-08-23
owners: orchestrator
related_requirements: [STRAT-008, SEC-005, SEC-006, NET-001, NET-002, OBS-006, REPORT-005, REPORT-006]
related_tasks: [T022, T033, T034, T040, T046, T047, T052, T053]
supersedes:
---

# ADR-011 — League-kit interoperability boundary, and the terminal-final/capture corrections it forced

## Context

The book (Reuven Segal, *Game-P2P-Cop-Chase*, v3.0.0) is the semantic authority for this project.
It fixes transport (MCP/FastMCP), the game, commit-reveal, `config/game.json`, and Gmail reporting,
but it does not ship byte-level interop vectors. `copthief-league-protocol` (pinned commit
`ad6557626587e09146af4283a5e808e7001343c5`, MIT, https://github.com/Imreec/copthief-league-protocol)
fills that gap: machine-checkable vectors, a `reference-v3` sparring peer, and operational
corrections (capture corroboration, the terminal-final scent exemption, per-sub-game lifecycle
requirements) surfaced by two independent teams' live cross-play. K0 (`python verify_vectors.py`
at the pinned commit) reproduces exactly the reviewed baseline: 125 checks across 15 fixtures (7
CORE, 4 PROMOTED, 2 PROPOSED, 2 ENH), all passing.

Neither peer's merged Replay work (T033/T034/T046/T047) nor its domain layer was built against
this kit. Two gaps matter:

1. **Wire shape.** T033's replay records and T046's internal bundle use a flat sealed-record
   representation. The kit's audit wire (§3 of `SPEC.md`) wraps the committed payload in a nested
   envelope: `{"payload": <exact original payload>, "nonce": ..., "commit": ...}`.
2. **Lifecycle.** The merged `PeerFacade.run()` negotiates once before a six-sub-game loop. The
   kit's `reference-v3` peer (and the book) requires one handshake **per sub-game**, with fresh
   per-sub-game runtime state and specific pairing-declaration semantics (§7.2–7.3 of `SPEC.md`).

Two corrections from the kit's own issue history (§3.1, credited to anrbj666/Alon Engel/Renat
Karimov and imreeyal) also invalidate assumptions this project carried into the merged work:

- A terminal `caught=true` final is **exempt** from the ordinary one-scent-advance-per-turn rule —
  both a zero-step resend and a one-advance final are legal, and a verifier must not require
  either specific transition.
- Peer-reported step counts need not be byte-identical: `abs(left_steps - right_steps) <= 1` is
  legal or explained by the two peers' different terminal-message perspective.
- A `caught=true` final is either an **answer** (echoes the cop's claimed cell — co-location) or a
  **concession** (names a different cell — rule 46/47). Both settle CAPTURE at the game layer, but
  the audit must corroborate them differently, and a corroboration failure must never be silently
  waved through, nor confused with cryptographic tampering.

## Decision

### Authority hierarchy (three, never collapsed)

1. **The book** is the semantic authority for game rules, transport, and submission requirements.
2. **The pinned kit commit** is the practical interoperability target for playing other teams —
   wire vectors, the `reference-v3` lifecycle, and its audit corrections.
3. **Our internal Replay bundle** (T046, `schema_status: internal_interop`) remains an
   application-owned format for our own evidence and debugging. It is not replaced.

These are tracked as three distinct, never-conflated status labels on any artifact or claim:
`internal_interop` (our T046 bundle), `kit_interop` (proven against the pinned kit), and
`official_schema` (only once INPUT-001/T016 supplies and we validate the actual official
templates — passing the kit does **not** imply this).

### Anti-corruption adapter, not a domain rewrite

Kit compatibility is implemented as a narrow adapter at the transport/application boundary
(new: T052's audit-envelope projection). It never leaks kit envelope types into scoring,
movement, or strategy. Preserved unconditionally:

- the internal flat sealed-record representation (T033/T034's own shape) as the record of
  record for internal Replay;
- T033's pure verifier and its support for both flat and nested decoding (strict — a shape
  that cannot be confidently parsed degrades coverage, it never guesses a shape from the first
  record alone, per the existing withheld-reveal-precedence discipline);
- the existing verdict taxonomy (`VERIFIED_OK`/`INCOMPLETE`/`INVALID`/`ILLEGAL`/`TAMPERED`) and
  layered coverage — kit interop adds a corroboration finding into this taxonomy, it does not
  add a sixth verdict;
- one commitment authority: outbound kit envelopes wrap the *original* committed payload
  unmodified — a kit adapter never re-hashes a widened or reshaped payload, which would create
  a second, competing commitment authority;
- local strategy authority and provider non-authority (ADR-010) — unaffected by kit interop;
- T046's internal bundle as-is — T053 is a *separate* projection boundary that generates the
  kit's four artifact kinds from the same settled series, it does not replace or rename T046's
  15-member bundle.

Canonical serialization for anything crossing the kit boundary matches the kit exactly: sorted
keys, compact separators, `ensure_ascii=False`, UTF-8, `SHA256(canonical_json(payload) + "|" +
nonce)` — a single `|` separator, per SPEC §4's explicit warning that all three plausible English
readings of that formula are tried in the wild and two of them fail every handshake silently
under self-test. A non-ASCII (Hebrew + emoji) conformance case is required specifically because
`ensure_ascii=True` is the kind of default that passes every English-only test and fails the
first real opponent.

### Per-sub-game lifecycle (T052)

`reference-v3` compatibility requires, through the *public* composition root (`create_peer` /
`PeerFacade.run`), not a diagnostic hand-rolled loop:

- one handshake before every sub-game, not one before the series;
- `sub_game_number` 1–6, actual alternating `role`, thief-first turn order in every sub-game;
- fresh runtime state per sub-game — position, barriers, inbox, nonce stream, commitment ledger,
  terminal flags never leak across the sub-game boundary;
- stable `game_id`/`game_uid` for the whole series once the first verified opponent is pinned;
  an unexpected opponent change refuses rather than silently re-pinning;
- SPEC §7.2/§7.3's PROMOTED-vs-PROPOSED declaration discipline: `role`/`sub_game_number` pairing
  is PROMOTED (a mismatch refuses), `game_uid` declaration is PROPOSED (omission is silence, a
  declared-and-mismatched value refuses).

### Terminal-final and capture corrections (supersede prior assumptions)

- The ordinary one-scent-advance rule does not apply to a terminal `caught=true` final; both a
  zero-step resend and a one-advance final are legal, and the receiver must not require either.
- Peer step counts may differ by at most one, explained by terminal-message perspective, without
  that alone being a fault.
- Answer-vs-concession corroboration (SPEC §3.1) is a **new required audit check**, layered onto
  the existing taxonomy: a hash/equivocation/withheld-reveal fault is still `TAMPERED`; a
  consistently-hashed but physically/semantically false capture claim is a corroboration failure
  (`ILLEGAL`, or an explicit disputed-capture-evidence finding — never silently accepted, never
  relabeled as cryptographic tampering); a payload with no parseable position degrades coverage,
  it is not an accusation.

### Kit governance tasks

- **T052** — the minimum production changes for `reference-v3` protocol/lifecycle compatibility
  (adapter, per-sub-game negotiation, terminal-final/capture corrections). Reviewed in Police
  first as the source implementation where the change is a shared/common concern; ported to
  Thief byte-for-byte where the code is genuinely shared, and semantically where it is
  role-specific (never a blind package-name find-and-replace).
- **T053** — a separate artifact-projection boundary that emits the kit's four artifact kinds
  (one declaration, six configs, six logs, one result — 14 JSON files for a six-sub-game series,
  a sparring-only marker is not one of the 14) from the same settled series T046 already
  captures. Labeled `kit_interop`, never `official_schema`.
- **T022** (amended, not replaced) — owns the external live two-process kit runs (K2), the kit's
  own vector/artifact/replay checkers (K0/K1/K3), and LLM-invariance-under-kit-play (K4).
  `G-LIVE` resolves only for the pinned, uncounted sparring target once these pass; it does not
  resolve counted-play or official-template gates.

## Consequences

- Two additional runtime environments are required for live kit runs: the kit's own
  (`fastmcp>=2,<3`) and this project's (FastMCP 3.x) — run as separate OS processes with separate
  interpreters; the two dependency locks are never merged to straddle incompatible FastMCP
  majors.
- T050 (selected vendor LLM) remains unaffected and still `BLOCKED_EXTERNAL: PLANQ-003` — a
  commercial LLM is not required for kit interoperability (K4 runs template/fake-provider only).
- Passing K0–K4 proves `kit_interop` against one specific external peer implementation. It is
  evidence of practical readiness to play other teams; it is not, and must never be reported as,
  `official_schema` compliance, which stays gated on INPUT-001/T016.
- Any kit fixture or code copied into either repo for `kit_interop` testing preserves the
  kit's MIT license, its source URL, and the pinned commit hash in the copy's provenance note.
