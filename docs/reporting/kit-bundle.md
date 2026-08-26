# Official Appendix-F projection (`kit_bundle.py`)

`build_kit_bundle` is the single outward projection of a settled `SeriesResult`. It consumes
complete signed identities, the agreed shared configuration, sealed audit records, both real
Git commits, and truthful per-sub-game token evidence. Missing or unknown mandatory evidence
raises; nothing is replaced with `unknown`, a fabricated zero, or an inferred opponent value.

For six sub-games it builds exactly 14 schema-version 1.1 documents: one declaration, six
configs, six logs, and one result. Configs carry the complete agreed shared structure. Logs
wrap the exact committed payloads. Result totals are recomputed from rows, and agreement
covers the complete rows and aggregate.

`publish_kit_bundle` stages the set under `<artifact_root>/official/<game_uid>/`, reloads it,
checks exact filenames, identifiers, links, config and commitment hashes, signed identities,
Git/token evidence, Israel-time timestamps, derived scores, log references, and confirmed
agreement, then publishes with one atomic rename. Existing destinations are never overwritten.

Use:

```bash
uv run python scripts/validate_official_artifacts.py <artifact-root>/official/<game_uid>
```

The internal replay set remains independently available under `replay/<game_uid>/`.
