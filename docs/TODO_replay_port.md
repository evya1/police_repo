# TODO — Replay (police_repo)

## ORC-R0 — governance (`claude-opus-5`, main effort High; orchestrator only)

- [x] Pin HEAD/status; preserve unrelated user changes. Police `16c3501`, Thief `59a8e7a` merged into `claude/police-thief-replay-llm-fzlztr`.
- [x] Resolve task-ID collision if present; update board and dependencies. Thief's replay tasks already carry T046/T047; the merge preserved that and did not reintroduce the T035/T036 duplicates.
- [x] Approve ADRs: ADR-008 verdict/coverage taxonomy and trust statement; ADR-009 internal-interop atomic bundle.
- [x] Install task packets with exact write sets; verify no overlap. `check_planning_graph.py` reports zero new issues against the pre-governance baseline.
- [x] Make T015 depend on T047 and remove replay-hash logic from the GUI task.

## T033 — pure replay core (`claude-sonnet-5`)

- [ ] Add frozen types and strict record codecs.
- [ ] Remove first-record/regex shape inference.
- [ ] Implement pure config/log verification with exact identity checks.
- [ ] Add mutation, physics, malformed, empty, sequence, mixed-shape, and coverage tests.
- [ ] Split every touched code/test file below 150 logical lines.
- [ ] Copy approved shared bytes to sibling and prove parity.

## T034 — immutable evidence (`claude-sonnet-5`)

- [ ] Add `SubgameReplayEvidence` with tuples/canonical bytes.
- [ ] Preserve return semantics via explicit adapter at `SeriesResult` boundary.
- [ ] Prove six evidence entries, step zero first, both halves, and no alias mutation.
- [ ] Capture and verify the immutable opponent-commit ledger observed during live play.
- [ ] Prove live audit/series tests unchanged in outcome.

## T046 — atomic bundle (`claude-sonnet-5`)

- [ ] Pure builders emit internal-interop documents with shared identity.
- [ ] Manifest lists exact member names/digests.
- [ ] Writer publishes only after self-verification.
- [ ] Failure injection at each write leaves no final directory.
- [ ] Two concurrent publishers: exactly one wins and the first result is never overwritten.
- [ ] Existing destination is never overwritten.

## T047 — SDK/CLI/integration (`claude-haiku-4-5-20251001` scaffolding; `claude-sonnet-5` implementation/review)

- [ ] SDK is the only application entrypoint.
- [ ] CLI contains no hashing/physics/schema logic.
- [ ] Stable text/JSON output and exit codes.
- [ ] Cross-peer bundle verification.
- [ ] Cross-peer verification uses frozen fixtures/subprocess CLIs, never sibling imports.
- [ ] Run the replay smoke and parity scripts described in the shared test strategy.
- [ ] Real honest/tampered sanitized transcripts.

## Final gate

- [ ] `uv sync --locked --all-groups`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest` with >=85% global coverage
- [ ] line-cap, task-ID, dependency, no-secret, and all repository gates
- [ ] byte-identical `common/` replay slice across both repos
- [ ] `git diff --check`; no unrelated changes
