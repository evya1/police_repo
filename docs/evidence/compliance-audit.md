# Police repository compliance audit

**Status:** complete  
**Audit date:** 2026-08-24  
**Branch audited:** `production-fixes`

## Release gate results

| Check | Result |
| --- | --- |
| `uv sync --locked --all-groups` | Pass; 104 packages resolved, 101 audited |
| `uv run ruff check .` | Pass; zero violations |
| `uv run pytest` | Pass; 1,527 passed, 2 skipped, 87.26% coverage |
| `scripts/check_markdown_links.py` | Pass; 154 Markdown files |
| `scripts/check_docs_present.py` | Pass; all 17 required documents |
| `scripts/run_quality_gates.py` | Pass; all seven repository gates |
| `git diff --check` | Pass |
| Replay GUI `--verify-only` | Pass; 72 g01 records re-hashed and verified |
| Full replay audit | Pass; 309 records, six verified subgames, zero issues |
| Reciprocal sibling parity | Pass; both generated bundles verified; no shared hash problems |

## Submission integrity

- Canonical game artifact: [`game.json`](games/ZeroOne0-vs-bestteam/game.json), SHA-256 `a701b8db8adabf3227a6c2c340a04246f46b25fab1f3c018ceb4d9b75dffe1da`.
- Counted game `ZeroOne0-vs-bestteam`, UID `a42b2bb2-2312-c679-5e69-fa3d5ea0aad9`, is settled with `audit_ok: true` in all six subgames.
- Live and Replay screenshots decode at 970×690 and are linked from the README.
- All 23 generated OpenRouter model/provider hyperlinks returned HTTP 200; all 15 committed provider assets decode locally.
- OpenRouter request counts, token counts, costs, percentages, and provider memberships are unchanged by the presentation mapping.
- The private OpenRouter input remains outside the repository.
- Superseded question IDs and stale group codes are absent from tracked submission content.
- [`LICENSE`](../../LICENSE) matches the required Educational Use EULA, SHA-256 `b8f5904d8625f22f18f3d6217b4cf066bf3c921fe895fcb8a324b690a63f8a06`.

## AI usage block

The pre-presentation checksum was `f5f6b268ac8e6f0e07d291f6247166f2f0c5d4e6010a960389a692d7e822b8a4`. The final checksum is `b38d0f1ab6cb41b80f2402b5a941f00ae4bf138b33dddb2a50fc145b26a1a5d8`; only the authorized model/provider presentation changed, while every numerical value and calculation remains unchanged.
