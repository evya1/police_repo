# Kit reference bundle — pinned fixture

Copied verbatim from the league interoperability kit's own example pairing bundle.

- Source: `https://github.com/Imreec/copthief-league-protocol`
- Commit: `ad6557626587e09146af4283a5e808e7001343c5`
- Path: `examples/pairing-artifacts/`
- Copied: unmodified, byte for byte.

## Why it is here

These files are the shape our projection targets, and the `result_*.json` in particular is the
only published artifact whose `mutual_agreement.sha256` was produced by a third party. Our
`tests/contract/kit_artifacts/test_kit_settlement.py` re-derives that digest from the rows in
this file. That assertion is the whole of the consensus contract: serialization form, preimage
scope, and row-key set, all pinned to bytes we did not write.

The bundle is synthetic — the kit states plainly that no game was played to produce it — so it
is evidence about a FORMAT, never about a match. Nothing here is a result of ours.
