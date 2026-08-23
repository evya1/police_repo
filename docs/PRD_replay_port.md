# PRD — Replay evidence and offline verification (police_repo)

## Outcome

`police_repo` shall publish a complete, immutable, offline-verifiable replay bundle after every completed series. The bundle shall re-check commitments through the existing canonical path, apply physics only when the evidence supports it, and expose one application use case to CLI and future GUI adapters.

## Users

- A partner team verifying copied match evidence without network access.
- CI proving an honest bundle succeeds and a one-byte mutation is detected.
- The evaluator inspecting declared configuration, two-sided logs, result, and token evidence.

## Functional requirements

- **RP-01 Strict decoding:** every log/config/record is decoded into frozen types. Booleans are rejected where integers are required; nonce is non-empty; commitment is 64 lowercase hex; steps are unique, ordered, contiguous from 0.
- **RP-02 Exact pairing:** `log_<game_id>_g<NN>.json` is verified only with `config_<game_id>_g<NN>.json` sharing `game_uid`, `game_id`, and `sub_game_index`. Zero/multiple matches are not success.
- **RP-03 Complete bundle:** one declaration, six configs, six non-empty logs, one result, and one internal manifest are required. Unknown JSON files are ignored only outside the selected UID directory; unexpected members inside it are `INVALID`.
- **RP-04 Verdict honesty:** hash/binding evidence failure is `TAMPERED`; intact-hash physics failure is `ILLEGAL`; syntax/type/identity failure is `INVALID`; missing artifacts/records are `INCOMPLETE`.
- **RP-05 Coverage honesty:** the report names separately whether integrity, captured live binding, physics, outcome, bundle digests, and external authenticity were checked. Supported foreign halves receive only supported layers. Mixed shape in one half is `INVALID`.
- **RP-06 Evidence capture:** `common/transport/subgame.py` returns immutable replay evidence containing both record halves, the opponent commitments observed live, result claims, signed terms bytes, and subgame identity. No mutable inbox ledger is retained.
- **RP-07 Atomic publish:** `police_peer.reporting.replay_bundle` serializes all documents, self-verifies them in a staging directory, then renames to `replay/<game_uid>`. Existing destination means fail closed; no overwrite.
- **RP-08 Interop label:** every emitted document says `schema_status: internal_interop` until T016/INPUT-001 is complete. No field is described as official.
- **RP-09 Application API:** `police_peer.sdk` exposes the replay use case. `scripts/replay.py` is argument parsing/printing/exit-code mapping only. Future T015 GUI consumes `ReplayReport` and performs no hashing.
- **RP-10 Cross-repo parity:** the shared files and shared tests in Police/Thief are byte-identical. Role-specific imports exist only outside `common/`.
- **RP-11 Trust honesty:** internal consistency is not called historical authenticity. Until an approved peer receipt/signature is verified, `external_authenticity` is false even when all local checks pass.
- **RP-12 Cross-document completeness:** manifest/result/log record counts and final steps agree for both halves, preventing a truncated final record from passing merely because the remaining sequence is contiguous.

## Non-goals

- Reconstructing the official four JSON schemas without their templates.
- Re-proving live commit binding that is not present in offline evidence.
- Adding a database, generic repository, UoW, event bus, DI framework, or runtime sibling import.
- Building the GUI in this workstream.

## Acceptance gate

1. Full `uv run ruff check .`, full `uv run pytest`, coverage >=85%, line-cap, task-ID, no-secret, and repository quality gates pass in both repos.
2. Honest real-series bundle: `VERIFIED_OK`, 6/6 logs, both halves and observed commitments counted, one UID, explicit unanchored authenticity status.
3. One-byte payload mutation: `TAMPERED` with file, half, and step.
4. Clean commitment plus diagonal/out-of-bounds/quota/step-ceiling violation: `ILLEGAL`, never `TAMPERED`.
5. Missing log, empty log, wrong config, duplicate config, malformed JSON, mixed UID: never success and mapped to the correct verdict.
6. A recomputed unanchored copy may remain internally consistent but is never reported authentic; comparison with the peer-observed commitment ledger detects divergence.
7. `diff -rq common/` and recorded SHA-256 hashes prove shared parity with `thief_repo`.
