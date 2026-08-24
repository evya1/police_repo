---
artifact: adr
id: ADR-013
status: accepted
date: 2026-08-24
owners: orchestrator
related_requirements: [REPORT-007, REPORT-008, REPORT-009, SEC-008, SEC-010, LEAGUE-001, LEAGUE-006]
related_tasks: [T057, T058]
related_contracts: [CT-08]
supersedes:
---

# ADR-013 — Declared identity, and refusing to report without agreement

## Context

Two rules in Appendix E are unusually expensive and pull in opposite directions.

Rule 35 zeroes **both** teams when two counted reports contradict each other — including the
side that got everything right. Rules 37–38 make a false declaration project-fatal. So a peer
must say a great deal about itself (identity, hardware, model, commit, game counts), all of it
checkable after the fact, and must never say any of it wrongly.

The declaration is where that lands. It is also the artifact with the most opportunity to
quietly invent something: a hardware spec nobody supplied, a commit that was not read, an
opponent's game count we cannot possibly know.

## Decision

**1. Nothing is invented; a missing field raises by name.** `GroupIdentity.__post_init__`
requires every field explicitly. There is no placeholder, no empty-string default that could
reach an artifact, and no "unknown" sentinel that reads as a value. An identity assembled from
defaults would look exactly like a true one, which is the whole problem.

**2. Hardware travels as a digest, not as a spec.** The greeting carries
`hardware_spec_sha256`; the full spec appears only in our own declaration block. An opponent
cannot verify our RAM, and a value nobody can check does not belong on a wire.

**3. The per-group signature is sign-then-insert, with a `sha256:` prefix.** The digest covers
the block as it stood before the `signature` key existed. The consensus digest in
`kit_consensus` is deliberately *unprefixed* and computed over a different scope in a different
serialization form — they are different fields proving different things, and making them look
alike would invite exactly one confusion too many.

**4. The greeting extension is purely additive and can never refuse.** `our_greeting` gains an
optional `identity_block`; `verify_greeting` is untouched. SPEC §7's stance is to refuse only
when both sides declare and disagree, so an opponent who declares less than we do — or
declares a key we have never heard of — is not at fault. Every pre-existing golden vector
passes unchanged.

**5. Agreement is decided on one value, and silence is not assent.** `evaluate` compares the
consensus digest and nothing else: that digest already covers everything two honest peers must
produce identically and nothing they may legitimately differ on, so comparing more would
manufacture disputes. An opponent who never answered has confirmed nothing.

**6. The refusal invents no sanction.** `assert_reportable` declines to send a report for a
counted series that was never agreed. It does not zero anyone, dock anyone, or record a
verdict. What the missing-report penalty actually is remains an open question with the course
staff (OPEN-004), and guessing at one would be worse than declining to send.

**7. Counts are exclusive before, inclusive after.** `counted_games_played` (declaration)
excludes the series being played; `games_played_including_this` (result) includes it. For a
counted series the identity is `inclusive == exclusive + 1`. An opponent count we did not learn
from their greeting is `null` — unclaimed — never `0`, which would be a claim that they have
played nothing.

## Consequences

* A counted run cannot start with an incomplete identity, so the failure surfaces before a game
  exists rather than at an artifact.
* The private TOML gains the App. B §4 sections. All are optional with safe defaults, because a
  warm-up on a laptop must run without a filled-in declaration; counted play is where the
  missing pieces are refused.
* `[email].mode` defaults to `dry-run` and `[email].recipient` to the lecturer's address:
  sending is opt-in, and a typo'd override should look wrong rather than silently mail nobody.

## Alternatives considered

**Compare whole reports rather than a digest.** Rejected: a report carries per-side timestamps
and token counts, so two conformant peers could never produce equal ones. That is the mistake
that makes agreement structurally impossible.

**Treat a timeout as agreement to keep a series reportable.** Rejected outright. It converts a
protocol failure into a false claim, and the party it hurts is the opponent.
