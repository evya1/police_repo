---
artifact: adr
id: ADR-012
status: accepted
date: 2026-08-24
owners: orchestrator
related_requirements: [REPORT-005, REPORT-006, REPORT-007, OBS-006, SEC-005, SEC-006]
related_tasks: [T053, T056]
supersedes:
---

# ADR-012 — The kit bundle is a projection, not a second emission path

## Context

Both peers already produce an internal 15-member replay bundle whose records are sealed,
audited, and verifiable end to end. Run against the pinned league kit
(`copthief-league-protocol` @ `ad6557626587e09146af4283a5e808e7001343c5`), that bundle
nevertheless produced:

```
python tools/check_artifacts.py <bundle>            ->  16 FAILURE(S)
python -m sparring.cli replay  <bundle>             ->  0 verified, 6 tampered
```

The obvious reading — that our sealing is wrong — is not what the evidence says. Re-hashing
each internal record under the kit's own construction,
`SHA256(canonical(record - {nonce, commit}) + "|" + nonce)`, reproduces **every stored commit
with zero mismatches**. `common/transport/ids.py` (`game_id`, `game_uid`, `terms_signature`)
and `common/transport/terms.py` (the flat 14-key table) already match the kit's reference
functions exactly.

The two failures decompose as:

* **16 checker failures = 6 distinct naming causes.** The declaration lacks `groups` and
  `num_sub_games`; configs emit `sub_game_index` where the kit requires `sub_game_number`;
  logs carry no `summary`; the result lacks `groups`, `num_sub_games` and `final_result`, and
  its rows are record-count summaries rather than score rows.
* **`0 verified, 6 tampered` = one shape cause.** Our records are flat
  (`{**payload, "nonce": ..., "commit": ...}`); the kit's auditor reads `record["payload"]`
  and finds nothing to re-hash. Every record fails the presence guard before any hash is
  attempted. The word "tampered" here describes a missing key, not a broken commitment.

## Decision

The kit bundle is a **pure projection of immutable evidence**. Concretely:

1. Nothing in the projection path re-hashes a game payload, re-canonicalises a sealed record,
   or mints an identifier. The only record reshaper is the existing
   `common/transport/league_kit_envelope.wrap_outbound_records`, which wraps the exact bytes
   that were already committed.
2. `ids.py`, `terms.py` and `canonical.py` are untouched.
3. Schema-shaped knowledge is confined to `kit_names.py`, `kit_documents.py` and
   `kit_records.py`, so that an official schema — still an unresolved external input
   (INPUT-001) — becomes a change to those modules and nothing else.
4. Every emitted document declares `schema_profile: "league-kit-reference-v3"`. No document
   claims official compliance.
5. The internal 15-member bundle at `<artifacts>/replay/<game_uid>/` is **kept unchanged**. It
   is richer evidence than the kit format and both peers' replay CLI already consume it. The
   kit bundle is written alongside it at `<artifacts>/kit/<game_uid>/` as one flat directory
   of exactly 14 files — the kit reads one flat directory by design.

## Consequences

* The change is confined to document shape, so it cannot alter what any past game proved.
* Two bundle layouts now exist and must not drift; the emission path derives both from the
  same `SeriesResult`, so a divergence is a code change rather than an accident.
* A future official schema replaces the three named modules and leaves the evidence, the
  sealing, the audit and the internal bundle untouched.

## Alternatives considered

**Re-emit records in the kit's shape at seal time.** Rejected: it would move a wire concern
into the integrity core, and it would make the commitment authority ambiguous — there must be
exactly one, and it is already the seal.

**Adopt the kit shape as our only bundle.** Rejected: the internal bundle carries live-binding
evidence (`opponent_committed_steps`) and a completeness manifest that the kit format has no
place for, and both are consumed by our own verifier.
