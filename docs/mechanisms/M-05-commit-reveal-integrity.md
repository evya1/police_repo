---
artifact: mechanism-prd
id: M-05
component: C03
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# M-05 — Commit-Reveal & Audit

## Why this mechanism has its own PRD

This is the central integrity algorithm of the whole system: every accepted step's legitimacy rests on it, and OPEN-007 leaves its exact canonical bytes undetermined. The ambiguity needs one precise, addressable home instead of being restated (and risking drift) in T008, T015, and T022's task files independently.

## Governing requirements

SEC-001 (SHA-256 Commit-Reveal on every step), SEC-002 (protocol order), SEC-003 (commitment binds State/Move/Intent/Nonce minimum), SEC-004 (fresh secret Nonce), SEC-005 (mutual end-of-game audit), SEC-006 (TAMPERED sanction, no repair), SEC-007 (truthful Capture Claim response).

## Specified behavior (binding)

- Every game step is protected by a SHA-256-based Commit-Reveal protocol (SEC-001) in the fixed order **Commit → Acknowledge → Reveal**, with **Final Reveal/Audit** at game end (SEC-002).
- The commitment binds at least `State`, `Move`, `Intent`, and `Nonce` for the step; no envelope field beyond supplied official material may be invented (SEC-003).
- Each commitment uses a fresh, unique cryptographic Nonce that remains secret until final audit (SEC-004).
- At game end, both sides perform a complete mutual log audit, reveal all Nonces, and recompute commitments (SEC-005). A single hash mismatch is marked TAMPERED and causes technical loss/disqualification, with no retrospective repair (SEC-006).
- During a Capture Claim the responding side must tell the truth; a false declaration or a false denial causes immediate disqualification (SEC-007).

## What is genuinely open (OPEN-007)

The book binds at least State/Move/Intent/Nonce but references a richer record without specifying it fully. Unresolved: exact Nonce placement inside vs. appended to the preimage; Unicode escaping rules; canonical key/field separators; whether the report-consensus signature is computed before or after the commitment hash; and the exact relationship between `game_uid` and `game_id`.

## Internal draft contract (explicitly non-official)

Until OPEN-007 resolves, C03 may build and test Commit-Reveal against an internal draft canonicalization, provided every artifact produced from it is labeled non-official and no cross-peer counted match uses it. See `planning/contracts/CT-04-canonical-bytes.md` for the exact draft shape and its compatibility-test matrix.

## Acceptance scenarios

- [ ] A clean Commit → Acknowledge → Reveal → Audit sequence over the local draft contract produces Verified OK. {#commit_reveal_happy_path}
- [ ] A one-byte mutation to the committed State, Move, Intent, or Nonce deterministically produces TAMPERED with no repair path. {#tamper_detection}
- [ ] A Nonce is never observable (logged, transmitted, or otherwise readable) before the audit phase. {#nonce_secrecy}
- [ ] Cross-peer canonical-byte fixtures are exercised only once OPEN-007 resolves. {#cross_peer_vectors}

## Owning task

T008 (`SEC-001…007`), depends on T003. Cross-peer fixtures gated at `{#cross_peer_vectors}` by OPEN-007; the happy-path and tamper-detection scenarios are unaffected.
