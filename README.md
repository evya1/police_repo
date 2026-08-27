# ZeroOne0 Police Peer

> A decentralized pursuit agent that hunts through partial information, seals every move, and proves every result without a central referee.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv locked](https://img.shields.io/badge/uv-locked-DE5FE9?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![CI](https://github.com/evya1/police_repo/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/evya1/police_repo/actions/workflows/ci.yml)
[![License: Educational Use EULA](https://img.shields.io/badge/License-Educational_Use_EULA-8A2BE2)](LICENSE)

**Course:** [Final Project](docs/PRD.md) · **Group:** [`ZeroOne0`](docs/evidence/games/ZeroOne0-vs-aviayeli/README.md) · **Sibling:** [Thief repository](https://github.com/evya1/thief_repo)

| Live GUI — local truth and belief | Replay GUI — verified result |
| --------------------------------- | ---------------------------- |
| [![Police Live GUI](docs/assets/live-gui.png)](docs/assets/live-gui.png) | [![Police Replay GUI](docs/assets/replay-gui-verified.png)](docs/assets/replay-gui-verified.png) |

**Live GUI:** actual runtime output; the local player sees its own local state and belief representation while the opponent's hidden state remains private.

**Replay GUI:** revealed tracks are displayed after transcript and commitment verification succeeds.

## 60-second verified demo

Run from the repository root. It installs the locked environment, runs the quality gate, completes a credential-free loopback series, verifies the real counted match through the Replay GUI service, and audits all six subgames.

```sh
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
DEMO_ROOT="$(mktemp -d)"
uv run python scripts/smoke_replay_integration.py \
  --config config/game.json --artifact-root "$DEMO_ROOT" --json
uv run python scripts/validate_official_artifacts.py \
  docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c
uv run python scripts/replay_gui.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3 --verify-only
uv run python scripts/replay.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9 --json
```

Expected: Ruff and pytest pass; the loopback result is settled with `replay_verdict: verified_ok`; the submitted Avi bundle validates; Replay GUI verification reports `verified_ok`; the audit reports six verified subgames and zero tampered subgames.

## What the agent does

The Police peer pursues from a probability distribution rather than hidden opponent truth. Its deterministic policy targets a confident belief peak, then scent evidence, then board centre; barrier scoring concentrates likely Thief locations while preserving Police reachability.

The peer also:

- owns only local truth and never sends objective hidden state to strategy or Live GUI;
- exchanges natural-language hints and protocol messages over FastMCP;
- commits before reveal, validates peer evidence, and rejects tampering;
- completes six-subgame series with alternating roles and deterministic scoring;
- publishes replay, declaration, configuration, log, result, audit, and reporting evidence;
- keeps optional model wording and Gmail delivery behind one rate-limited Gatekeeper.

## System architecture

| Layer | Responsibility | Primary location |
| --- | --- | --- |
| Domain/config | Board rules, movement, barriers, scoring, shared contract | `common/domain/`, `config/` |
| Belief/scent | Local opponent distribution and deterministic observations | `src/police_peer/belief/` |
| Strategy | Role-specific action choice; no objective opponent state | `src/police_peer/strategy/` — pursuit and barrier policy |
| Runtime | Lifecycle, deadlines, retry, recovery, six-game orchestration | `src/police_peer/runner.py` |
| Transport | Symmetric FastMCP server/client and wire profiles | `common/transport/` |
| Integrity | Canonical bytes, Commit-Reveal, replay and audit | `common/transport/canonical.py`, `common/transport/audit.py`, `common/transport/replay.py` |
| Reporting | Replay/kit bundles, agreement, Gmail composition | `src/police_peer/reporting/` |
| UI | Production Live GUI and verified read-only Replay GUI | `src/police_peer/live_gui.py`, `src/police_peer/replay_gui.py` |

The programmatic entry point is [`src/police_peer/sdk.py`](src/police_peer/sdk.py). Architecture decisions and protocol boundaries are documented in [`docs/PLAN.md`](docs/PLAN.md) and [`docs/contracts/`](docs/contracts/).

## Game and protocol flow

1. Both peers load the same shared JSON contract and lock its digest.
2. Step 0 exchanges identity, repositories, role commits, model declaration, and protocol profile.
3. The acting peer derives a legal move from local state, scent, and belief.
4. State, move, intent, and nonce are sealed before the peer receives the reveal.
5. FastMCP transports the symmetric request/response without a central judge.
6. Each peer validates legality, ordering, deadlines, commitments, and revealed records.
7. Belief and local runtime state advance; retry and watchdog logic preserve bounded recovery.
8. Six subgames settle under the agreed role schedule and scoring table.
9. Result agreement, replay publication, audit, reporting, and GUI replay use the same immutable evidence.

Protocol details: [CLI](docs/CLI.md), [peer wire contract](docs/contracts/CT-03-peer-wire.md), [Commit-Reveal](docs/mechanisms/M-05-commit-reveal-integrity.md), and [result agreement](docs/contracts/CT-08-result-agreement.md).

## Installation

Prerequisites are Git and [`uv`](https://docs.astral.sh/uv/). Python 3.12 and all dependency versions are resolved from `uv.lock`.

```sh
git clone https://github.com/evya1/police_repo.git
cd police_repo
git checkout master
uv sync --locked --all-groups
```

No credentials are required for tests, local loopback play, replay, or audit verification. OpenRouter and Gmail integrations fall back or remain dry-run unless explicitly configured.

## Running a local match

This public-SDK smoke command composes both roles over an in-memory loopback, runs all six
subgames, and verifies the internal replay bundle:

```sh
LOCAL_ARTIFACTS="$(mktemp -d)"
uv run python scripts/smoke_replay_integration.py \
  --config config/game.json \
  --artifact-root "$LOCAL_ARTIFACTS" \
  --seed 42 \
  --json
```

For the production two-process warm-up and official 14-file output, follow
[Official Appendix-F reporting](docs/reporting/official-appendix-f.md). Valid official files
appear under `<artifacts>/official/<game_uid>/`; replay and outbox data remain separate.

## Running against an external peer

Copy `config/game.toml.example` to an untracked private file, fill only the publication-intended identity and runtime endpoint values, and agree on the byte-identical shared match contract before Step 0.

```sh
PEER_MCP_URL="https://opponent.example/mcp"
PUBLIC_MCP_URL="https://zeroone0.example/mcp"
uv run police-peer \
  --listen-host 0.0.0.0 \
  --listen-port 8101 \
  --peer-url "$PEER_MCP_URL" \
  --public-url "$PUBLIC_MCP_URL" \
  --shared-config config/game.json \
  --private-config config/game.toml.example \
  --group-id ZeroOne0 \
  --group-code-confirmed \
  --mode counted \
  --wire-profile reference-v3 \
  --artifacts-dir artifacts/counted
```

The opponent runs its symmetric role command. Public URLs are operator-supplied; secrets, OAuth files, private endpoints, and keys are never committed. See [configuration](config/README.md).

## GUI usage

Start the production peer with its local-truth window:

```sh
uv run python scripts/live_gui.py \
  --mode live \
  --shared-config config/game.json \
  --artifacts-dir artifacts/live
```

Open the verified real-match replay:

```sh
uv run python scripts/replay_gui.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3
```

Use `--verify-only` on a headless host. The Live GUI receives redacted production events; Replay remains read-only and reveals both tracks only after verification.

## Replay and audit verification

Headless Replay GUI verification:

```sh
uv run python scripts/replay_gui.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3 --verify-only
```

Full six-subgame immutable-bundle audit:

```sh
uv run python scripts/replay.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9 \
  --json
```

Cross-repository parity:

```sh
uv run python scripts/check_replay_parity.py \
  --sibling-root ../thief_repo
```

Exit `0` means verified; replay verification distinguishes illegal, invalid/incomplete, and tampered evidence with dedicated nonzero statuses.

## Submitted match result

The selected final league report and its full evidence index are documented in
[`docs/evidence/games/ZeroOne0-vs-aviayeli/README.md`](docs/evidence/games/ZeroOne0-vs-aviayeli/README.md).

| Field | Confirmed value |
| --- | --- |
| Game ID | `ZeroOne0-vs-aviayeli` |
| Game UID | `ff90bd18-f873-981a-e1ca-0b89e6f9f03c` |
| Mode | `counted` |
| Opponent | `aviayeli` |
| Natural role | Police |
| Series | Six completed subgames; mutual agreement confirmed |
| Roles | ZeroOne0 Thief in 1, 3, 5; Police in 2, 4, 6 |
| Final score | ZeroOne0 40 — aviayeli 60 |
| Counted-night consensus | `c39d331ce8c45e30823baf2aeae58053020836542aa6e14d584fa2a58af23ee6` |
| Full post-game settlement | `5077306a3703467941ce7593bcf805a022c9f162588acc4f3feca97a045b0373` |

The Gmail API acknowledged the single selected ZeroOne0 result attachment. The
older completed series against `bestteam` remains available as
[additional historical match evidence](docs/evidence/games/ZeroOne0-vs-bestteam/README.md);
it is not presented as the selected final-report submission.

## Evidence and submission artifacts

| Evidence | Repository path |
| --- | --- |
| Submitted match evidence index | [`ZeroOne0-vs-aviayeli/README.md`](docs/evidence/games/ZeroOne0-vs-aviayeli/README.md) |
| Declaration/identity evidence | [`declaration_ZeroOne0-vs-aviayeli.json`](docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/declaration_ZeroOne0-vs-aviayeli.json) |
| Six per-subgame configurations | [`official/ff90bd18.../`](docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/) |
| Six logs and transcript records | [`official/ff90bd18.../`](docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/) |
| Appendix-F result | [`result_ZeroOne0-vs-aviayeli.json`](docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/result_ZeroOne0-vs-aviayeli.json) |
| Exact submitted attachment | [`submission-email/result_ZeroOne0-vs-aviayeli.json`](docs/evidence/games/ZeroOne0-vs-aviayeli/submission-email/result_ZeroOne0-vs-aviayeli.json) |
| Additional historical match | [`ZeroOne0-vs-bestteam/`](docs/evidence/games/ZeroOne0-vs-bestteam/) |
| GUI proof | [Live](docs/assets/live-gui.png) · [Replay](docs/assets/replay-gui-verified.png) |

Reporting composition, validation, settlement, replay publication, and Gmail delivery are documented under [`docs/reporting/`](docs/reporting/).

## Testing and quality gates

The release gate is reproducible locally and in [GitHub Actions](https://github.com/evya1/police_repo/actions/workflows/ci.yml):

```sh
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
uv run python scripts/check_markdown_links.py
uv run python scripts/check_docs_present.py
uv run python scripts/run_quality_gates.py
git diff --check
```

The suite enforces Ruff, 85% aggregate coverage, documentation presence, local Markdown links, task IDs, the 150-logical-line policy, secret/archive checks, and least-privilege workflows. Replay and parity commands above are part of release verification.

## Submission readiness

- [x] Completed Police implementation and production FastMCP wiring
- [x] Completed local-truth Live GUI and verified Replay GUI
- [x] Completed Commit-Reveal, replay, audit, and tamper rejection
- [x] Completed and submitted the selected six-subgame counted series against `aviayeli`
- [x] Preserved the validated 14-file bundle and exact submitted attachment
- [x] Completed reporting, agreement, declaration, and artifact integration
- [x] Completed tests, coverage, documentation, links, and quality gates
- [x] Confirmed group code `ZeroOne0` and sibling repository
- [ ] Publish a final annotated submission tag after this evidence commit

The final annotated tag will identify the exact submission release. No generated credentials, private email addresses, OAuth material, or secret material are part of the repository.

## Repository structure

| Path | Contents |
| --- | --- |
| `common/` | Shared deterministic domain, protocol, integrity, and replay code |
| `src/police_peer/` | Police-specific strategy, runtime, UI, SDK, reporting, and infrastructure |
| `config/` | Shared contract, role-local example, quality policy, completed match configuration |
| `scripts/` | Live/Replay entry points, smoke test, parity, quality, and reporting utilities |
| `tests/` | Unit, property, integration, interoperability, GUI, replay, and reporting tests |
| `docs/` | Architecture, contracts, mechanisms, detailed reports, tasks, and evidence |
| `docs/evidence/games/` | Completed real-match artifact bundles |
| `.github/workflows/ci.yml` | Locked install, Ruff, pytest/coverage, and repository gates |

## AI/LLM usage and costs

<!-- ai-usage:start -->
<!-- generated aggregate data only -->
## AI Usage

> [!IMPORTANT]
> ### Total AI / LLM Cost — **$679.43**
> **OpenRouter:** $44.94 · **Claude Code:** $410.76 · **Codex:** $223.73 estimated
>
> Sanitized aggregate project usage only — no secrets, credentials, personal identifiers, session IDs, request IDs, UUIDs, usernames, or private metadata are published.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/ai-usage-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/ai-usage-light.svg">
  <img alt="Aggregated OpenRouter, Claude Code, and Codex usage and cost" src="docs/assets/ai-usage-light.svg">
</picture>

This dashboard combines aggregated OpenRouter activity, the frozen Claude Code baseline, and a sanitized aggregate of completed Codex sessions. Only aggregate categories and calendar-day buckets are published.

### Reconciliation

| Metric | Aggregate |
| --- | ---: |
| Total AI / LLM cost | **$679.43** |
| OpenRouter spend | $44.94 |
| Claude Code accounted spend | $410.76 |
| Claude Code source-reported spend | $251.20 |
| Codex API list-price estimate | $223.73 |
| OpenRouter requests | 4,501 |
| Claude Code sessions | 18 |
| Codex sessions | 14 |
| Combined non-cache input / prompt tokens | 335,778,463 |
| Combined non-cache output / completion tokens | 4,839,697 |

OpenRouter activity: `2026-08-17` through `2026-08-27` across 7 calendar-day buckets. Codex covers completed session data from `2026-08-24` through `2026-08-25`. No Claude Code date range was inferred. Requests and sessions remain separate activity units.

### Claude Code model summary

| Model | Session appearances | Input | Output | Cache read | Cache write | Attributed cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Opus 5 | 12 | 21,178 | 499,000 | 1,058,600,000 | 31,504,200 | $197.17 |
| Sonnet 5 | 7 | 3,887 | 31,910 | 508,600,000 | 13,444,900 | $38.19 |
| Opus 4.8 | 1 | 877 | 3,200 | 190,200,000 | 10,300,000 | $159.56 |
| Haiku 4.5 | 1 | 452 | 106 | 1,800,000 | 508,200 | $0.19 |
| Unallocated multi-model session | — | — | — | — | — | $15.65 |
| **Total** | **18 sessions** | **26,394** | **534,216** | **1,759,200,000** | **55,757,300** | **$410.76** |

Opus 4.8 is a $159.56 list-price equivalent calculated from [Anthropic's standard pricing](https://platform.claude.com/docs/en/build-with-claude/prompt-caching): $5/M input, $25/M output, $6.25/M default five-minute cache writes, and $0.50/M cache reads. Other Claude costs remain source-reported.

Session appearances are not additive because a session may use more than one model. Cache reads and cache writes are reported separately and are not treated as normal input tokens.

### Codex model summary

| Model | Session appearances | Non-cache input | Output | Reasoning output | Cache read | Cache write | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 14 | 9,484,067 | 1,466,599 | 494,310 | 391,165,184 | 0 | $223.73 |
| **Total** | **14 sessions** | **9,484,067** | **1,466,599** | **494,310** | **391,165,184** | **0** | **$223.73** |

Codex records do not include billed cost. The estimate uses [OpenAI's GPT-5.6 Sol promotional API pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol): $4.00/M non-cache input, $0.40/M cached input, $5.00/M cache writes, and $20.00/M output. Reasoning output is included in output and is not charged twice.

Codex sessions are deduplicated by private session linkage, but only aggregate counts are published. Token counters are taken at each thread's last completion marker; later aborted or incomplete work is excluded.

### OpenRouter model summary

| Model | Provider | Requests | Prompt tokens | Completion tokens | Total reported cost | Share of cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [Google: Gemini 3.7 Flash](https://openrouter.ai/google/gemini-3.7-flash) | Google | 3,077 | 249,543,651 | 1,613,321 | $23.81 | 52.96% |
| [Z.ai: GLM 5.2](https://openrouter.ai/z-ai/glm-5.2) | <a href="https://openrouter.ai/provider/baidu"><img src="docs/assets/providers/baidu.png" width="16" alt=""> Baidu Qianfan</a>, <a href="https://openrouter.ai/provider/crusoe"><img src="docs/assets/providers/crusoe.png" width="16" alt=""> Crusoe</a>, <a href="https://openrouter.ai/provider/decart"><img src="docs/assets/providers/decart.png" width="16" alt=""> Decart</a>, <a href="https://openrouter.ai/provider/friendli"><img src="docs/assets/providers/friendli.png" width="16" alt=""> Friendli</a>, <a href="https://openrouter.ai/provider/gmicloud"><img src="docs/assets/providers/gmicloud.png" width="16" alt=""> GMICloud</a>, <a href="https://openrouter.ai/provider/novita"><img src="docs/assets/providers/novita.png" width="16" alt=""> NovitaAI</a>, <a href="https://openrouter.ai/provider/siliconflow"><img src="docs/assets/providers/siliconflow.svg" width="16" alt=""> SiliconFlow</a>, <a href="https://openrouter.ai/provider/streamlake"><img src="docs/assets/providers/streamlake.png" width="16" alt=""> StreamLake</a> | 447 | 37,572,921 | 517,421 | $9.25 | 20.58% |
| [DeepSeek: DeepSeek V4 Pro 0813](https://openrouter.ai/deepseek/deepseek-v4-pro-0813) | <a href="https://openrouter.ai/provider/alibaba"><img src="docs/assets/providers/alibaba.png" width="16" alt=""> Alibaba Cloud Int.</a>, <a href="https://openrouter.ai/provider/gmicloud"><img src="docs/assets/providers/gmicloud.png" width="16" alt=""> GMICloud</a>, <a href="https://openrouter.ai/provider/novita"><img src="docs/assets/providers/novita.png" width="16" alt=""> NovitaAI</a>, <a href="https://openrouter.ai/provider/parasail"><img src="docs/assets/providers/parasail.png" width="16" alt=""> Parasail</a>, <a href="https://openrouter.ai/provider/siliconflow"><img src="docs/assets/providers/siliconflow.svg" width="16" alt=""> SiliconFlow</a>, <a href="https://openrouter.ai/provider/together"><img src="docs/assets/providers/together.png" width="16" alt=""> Together</a> | 291 | 16,184,856 | 438,093 | $4.83 | 10.74% |
| [Google: Gemini 3.1 Pro Preview](https://openrouter.ai/google/gemini-3.1-pro-preview) | Google | 76 | 3,382,625 | 28,152 | $2.14 | 4.74% |
| z-ai/glm-5.3-20260816 | Z.AI | 90 | 5,947,835 | 44,830 | $1.86 | 4.13% |
| anthropic/claude-4.5-haiku-20251001 | Amazon Bedrock | 144 | 4,369,961 | 33,791 | $0.97 | 2.15% |
| [DeepSeek: DeepSeek V4 Pro 0423](https://openrouter.ai/deepseek/deepseek-v4-pro) | <a href="https://openrouter.ai/provider/baidu"><img src="docs/assets/providers/baidu.png" width="16" alt=""> Baidu Qianfan</a> | 53 | 1,587,579 | 32,999 | $0.87 | 1.92% |
| anthropic/claude-4.8-opus-fast-20260528 | Anthropic | 14 | 211,650 | 4,426 | $0.69 | 1.52% |
| Other (18 models) | Multiple providers | 309 | 7,466,924 | 125,849 | $0.57 | 1.26% |

> Claude Code includes four sessions that source-reported $0.00. The Opus 4.8 list-price equivalent is included in accounted spend; one $15.65 multi-model session remains unallocated rather than assigning its cost to a model without evidence.

> Totals are calculated from full-precision values before public dollar amounts are rounded to two decimal places.

Regenerate with private inputs kept outside the repository:

```bash
python scripts/generate_usage_dashboard.py \
  --openrouter-input /private/openrouter-baseline.csv /private/openrouter-increment.csv \
  --claude-input data/claude-code-usage-aggregate.json \
  --codex-input data/codex-usage-aggregate.json \
  --output-dir docs/assets \
  --update-readme README.md
```
<!-- ai-usage:end -->

## Authors, course, and sibling repository

- **Team:** ZeroOne
- **Group code:** `ZeroOne0`
- **GitHub:** [evya1](https://github.com/evya1) · [Us5rName](https://github.com/Us5rName)
- **Course:** [Final Project requirements and implementation contract](docs/PRD.md)
- **Repositories:** [Police](https://github.com/evya1/police_repo) · [Thief](https://github.com/evya1/thief_repo)
- **License:** [Educational Use EULA](LICENSE), copyright © 2026 Dr. Yoram Segal / Gal Technologies Artificial Intelligence Ltd. (GTAI), all rights reserved

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development workflow. Use is limited by the binding terms in [`LICENSE`](LICENSE); licensing requests may be sent to `segal@gal-tech.ai`.
