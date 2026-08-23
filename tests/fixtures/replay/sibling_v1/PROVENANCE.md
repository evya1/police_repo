# sibling_v1 — frozen cross-peer replay fixture

Frozen internal-interop replay bundle (`schema_status: internal_interop`, RP-03) used by
`tests/integration/test_cross_peer_replay.py` to prove this repository's replay CLI/service
consumes a bundle it did not just generate in the same test run, without ever importing or
invoking the sibling `thief_peer` package at runtime.

## How this was produced

Generated once, offline, with this repository's own compliant publisher
(`police_peer.reporting.replay_bundle.publish_replay_bundle`) over six honest sub-games built
from `tests/unit/transport/replay_fixtures.py`'s deterministic `honest_steps`/`seal` helpers —
the same shared schema (`common/transport/replay.py`, `replay_types.py`) both peer repositories
implement byte-for-byte identically (see `scripts/check_replay_parity.py`). The sibling
repository was not run to create this fixture; it stands in for "a bundle from elsewhere" so the
cross-peer test does not depend on the sibling's own T047 work being complete yet.

## Provenance

Every member's SHA-256 digest is recorded in `manifest_A-vs-B.json` under `"members"`. The test
recomputes each digest from the checked-in bytes and asserts it still matches — any accidental
edit to a bundle file is caught the same way a tampered live bundle would be.

No secrets, private identifiers, or credentials are present; all identities (`game_id`,
`game_uid`) and content are synthetic.
