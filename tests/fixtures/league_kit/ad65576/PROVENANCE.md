# Pinned `copthief-league-protocol` vector fixtures

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/Imreec/copthief-league-protocol |
| Pinned commit | `ad6557626587e09146af4283a5e808e7001343c5` |
| License | MIT (`LICENSE`, copied verbatim beside these files) |
| Copied | 2026-08-23 |
| Copied by | T054 (portable kit fixtures) |

## Why these files are vendored

`tests/contract/test_league_kit_vectors.py` previously read the kit's vectors from a
hard-coded developer checkout at an absolute path under a personal home directory. That
made the contract suite silently *skip* wherever that path did not exist — including CI —
so a conformance regression could land green. The same suite's skip count changed purely
because a developer happened to have the checkout: on 2026-08-23 the Police suite reported
`1254 passed, 6 skipped` before that checkout existed and `0 skipped` afterwards, with no
code change between the two runs.

These four fixtures are the exact bytes of the pinned commit's vector files that the
contract test consumes. They are committed so the contract test always executes and never
skips for an environment reason.

## Files and hashes

Verify with `sha256sum -c` from this directory (`vectors/`):

| File | SHA-256 |
|---|---|
| `vectors/canonical_json.json` | `32cefe9d2efacc025580318af8bcc690705cd5966cdcabfadf5f03f2cb6b4d8c` |
| `vectors/commit_reveal.json` | `18be7cadf6a68597f3fb641da39bd4b4cb017c1feb62a1eff8bc0ef7fc62c4c9` |
| `vectors/game_uid.json` | `66b817da3210c5a793a6ed09de4f8e794487121a67ab9bd7ef555f9243ab5bb4` |
| `vectors/terms_signature.json` | `896a77d8f3ffa748c60a50d8473a5ef807b21883a7aebe454f63b53487222549` |

## Scope of the evidence

Reproducing these vectors proves byte-level agreement with the kit's canonical JSON,
commitment, signature and UID construction. It is `kit_interop` evidence only. It is **not**
`official_schema` evidence and does not authenticate anything against the course's official
report templates, which remain an external gate (INPUT-001 / T016).

Live checks against a full kit checkout (the four `K0` gates and the `K2` two-process runs)
still take an explicit `--kit-root`; they are never wired to a fixed path.
