---
artifact: adr
id: ADR-009
status: accepted
date: 2026-08-23
owners: orchestrator
related_requirements: [REPORT-005, REPORT-006, REPORT-007, REPORT-008, REPORT-009, OBS-006]
related_tasks: [T046, T047]
supersedes:
---

# ADR-009 — Atomic, race-safe publication of an internal-interop replay bundle

## Context

Replay artifacts at the reviewed baseline were written by independent `write_text` calls. A crash or
a cancellation between two of those calls leaves a directory that looks like a bundle, contains a
plausible subset of documents, and verifies as far as it goes. Partial evidence that resembles
complete evidence is worse than no evidence.

Two further problems appear once publication is made atomic in the obvious way. A check for an
existing destination followed by a rename is a time-of-check/time-of-use race: a second publisher
can win between the two operations. And a closed file is not a durable file — without fsync, a
bundle can be published and then lost or truncated by a crash.

Separately, the four official JSON templates are absent (INPUT-001 is `MISSING`). Any schema this
repository emits today is a local guess. Labelling a guess "official" would manufacture false
compliance.

## Decision

**Publication is all-or-nothing and race-safe.** The writer serializes every document in memory,
creates a unique sibling staging directory `<root>/replay/.<uid>.staging-<random>` with mode 0700,
writes the exact member set, flushes and fsyncs the files and the staging directory where the
platform supports it, computes digests, reloads and self-verifies all six config/log pairs, acquires
an **O_EXCL publication lock**, renames once, and fsyncs the parent directory where supported.

**Failure leaves nothing.** Staging is cleaned in `finally`. A failure injected after any individual
write, after fsync, or at publish leaves no destination directory and no staging residue.

**An existing bundle is immutable.** A destination that already exists is never overwritten; the
second publisher fails closed. A stale lock is *reported* for T022 recovery, never silently deleted —
deleting it is exactly how the race is reintroduced.

**Everything emitted is labelled `internal_interop`.** Every document carries `schema_version`,
`artifact_kind`, `schema_status: internal_interop`, `game_uid`, `game_id`, and, where applicable,
`sub_game_index`. The manifest lists exact member names and SHA-256 file digests and is the internal
transaction and completeness envelope — it is *not* claimed to be an official fifth submission
artifact. Cross-document expected record counts and final steps must agree for both halves, so a
truncated final record cannot pass merely because the remaining sequence is contiguous.

**The official route stays open and separate.** T016/INPUT-001 remains the only path to official
output. When the templates arrive, an official document adapter is added; the manifest is removed or
adapted only if the official templates prescribe another mechanism.

## Alternatives considered

- **Write documents in place and validate afterwards.** Rejected: this is the defect. The window
  between the first and last write is exactly where a partial bundle is born.
- **Write a single archive file instead of a directory.** Rejected: it complicates partner-team
  inspection and the CLI for no gain; directory rename is already atomic within a filesystem.
- **`exists()` check followed by rename.** Rejected: time-of-check/time-of-use race; two publishers
  can both pass the check.
- **Delete a stale lock automatically.** Rejected: indistinguishable from a live concurrent
  publisher. Recovery is T022's explicit responsibility.
- **Guess the official schema from the project requirements.** Rejected: it would create false
  compliance and quietly become the thing that is later hard to unpick.

## Consequences

Positive: a published UID directory is complete or absent, never in between; the bundle is durable
against crash; concurrent publishers cannot corrupt each other; and no document overstates its
standing relative to the official specification.

Negative: publication costs fsyncs and a lock, and the writer carries platform-conditional code for
systems without directory fsync. The `internal_interop` label must be removed deliberately later
rather than by default.

Interoperability: the sibling repository consumes this bundle through its own CLI in a separate
process; the shared verification bytes are identical, so a bundle that verifies in one repository
verifies in the other.

## Validation

- Failure injection after each write, after fsync, and at publish: no final directory, no residue.
- Two concurrent publishers race the same UID: exactly one wins, the loser fails closed, and the
  winner's bundle is byte-unchanged.
- An existing destination is never overwritten.
- Manifest membership, digests, and cross-document counts are checked on reload.
- A real settled series publishes a bundle that the SDK verifier reports `VERIFIED_OK`.
- Reciprocal Police/Thief verification runs as separate subprocesses without importing the sibling.

## Approval

- Decision owner: orchestrator
- Approved by: orchestrator (ORC-R0)
- Approval date: 2026-08-23
