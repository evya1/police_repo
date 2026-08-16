# P2P Police Peer

> **Status:** the C01 foundation is implemented on the integration branch — shared domain rules, board geometry, movement/barrier/capture legality, the fixed scoring table, and the configuration boundary, with unit tests. Everything above C01 is not started. No screenshots, benchmarks, league results, or completed-series evidence exist yet. Per-task state is in `docs/TODO.md`.

This repository implements the autonomous Police side of a two-peer Police/Thief system. It owns only its local truth and communicates with the sibling peer through FastMCP/MCP. The shared intent is in `docs/PRD.md`; the role-specific strategy is in `docs/PLAN.md`; execution state lives in `docs/TODO.md` and individual task files.

## Project overview

The target is a decentralized hidden-state pursuit game: the Police process maintains local state, opponent belief, scent evidence, a separate strategy, Commit-Reveal integrity, Live GUI, Replay, resilience, and signed reporting. Its strategy objective is to pursue through local belief, place truthful barriers, and make only justified capture claims.

Confirmed team metadata:

- Team name: `ZeroOne`
- Team number: `01`
- GitHub handles: `evya1`, `Us5rName`
- Repository URLs: `https://github.com/evya1/police_repo`, `https://github.com/evya1/thief_repo`

Candidate awaiting confirmation:

- Final-project group code: `ZeroOne1` — eight characters, recorded here as a candidate. It must be confirmed against a human-approved team record (OPEN-003, OPEN-010) before it is used in any submitted artifact.

Legal names, government identifiers, and other private identity fields are never stored in repository artifacts.

Sibling repository: <https://github.com/evya1/thief_repo>.

## Source-of-truth order

1. Official project specification and official software-quality guide.
2. Repository-local canonical requirements, open items, and traceability in `docs/spec/`, plus authoritative input status in `docs/inputs/INPUT_REGISTER.md`.
3. `docs/PRD.md` for intent and required behavior.
4. `docs/PLAN.md` for this repository's technical strategy.
5. `docs/TODO.md` and `docs/tasks/T###-*.md` for execution state and evidence.

Conflicts stop work and go to the orchestrator. Workers do not silently update the PRD, PLAN, task dependencies, or scope.

## Architecture

The architecture separates domain rules, scent/belief, police strategy, orchestration/state, FastMCP transport, integrity/audit, reliability, reporting, and GUI/Replay, exposing business behavior through one thin programmatic facade. See `docs/PLAN.md` for the boundaries and the target tree; a path in that tree is not an implementation-status claim.

Implemented today: shared domain and configuration modules under `common/`, the role re-export surface under `src/police_peer/domain/`, and the shared game contract at `config/game.json`. The programmatic facade, transport, integrity, orchestration, observability, and reporting layers are not started.

## Installation

Prerequisite: a compatible `uv` installation.

```sh
uv sync --all-groups
```

The runtime baseline is recorded as PLANQ-002 in `docs/spec/OPEN_QUESTIONS.md`: Python 3.12 as the CI baseline over a declared `>=3.12` range, FastMCP as a direct runtime dependency at `fastmcp>=3.4,<4`, and the existing test/quality tooling. T002 executes that baseline and commits the validated `uv.lock`; once it lands, use:

```sh
uv sync --locked --all-groups
```

Do not install with `pip` and do not create a separate `requirements.txt`.

## Usage

`TODO_BEFORE_SUBMISSION`: document the exact launcher, FastMCP endpoint, tunnel setup, warm-up/counted modes, GUI start, Replay command, controlled shutdown, and expected output only after those interfaces exist and have been verified.

Planned programmatic entry: `police_peer.sdk` (final public names are owned by T003).

## Configuration

- `config/game.json`: shared, identical, cryptographically locked match contract.
- `config/game.toml`: private role-local choices; it cannot override or weaken a shared value.
- `.env`: local secret-bearing environment only; never commit it.
- `credentials.json` and `token.json`: local Gmail OAuth material; never commit them.
- Optional language-model provider: T027 may implement a provider-neutral adapter only after PLANQ-003/PLANQ-004 approval. Template mode remains valid without a provider; any selected external provider uses the Gatekeeper and local secret configuration, with no credential variable predefined before selection.

See `config/README.md`. Official reporting templates and the remaining private/team values are still missing and must not be guessed.

## Academic and technical explanation

### Dec-POMDP framing

The two agents act under partial observation: each knows its own position and locally known state, observes opponent scent and natural-language hints, maintains a belief distribution, and selects an action without a central judge. Rewards follow the fixed capture/survival/tie rules. `TODO_BEFORE_SUBMISSION`: relate the implemented state, observation, action, transition, and reward code to this framing with precise file links.

### Discrete pursuit on a bounded graph

There is no external judge: both agents compute the same transition function and terminal conditions from one pre-agreed, byte-identical contract (`config/game.json`, `CFG-001`), so there is no dispute about legality before play starts. One orthogonal step or stay per turn with no diagonal movement (`GAME-004`, `GAME-005`) ties the game to the cops-and-robbers pursuit family studied in graph theory. The board's minimum size of 7×7 (`GAME-001`) keeps the joint state space — the product of both agents' positions and every barrier layout — large enough that brute-force search over it is not a viable strategy, which is why heuristic and learned policies (`STRAT-007`) are the intended approach rather than exhaustive enumeration. The barrier quota (`GAME-008`) makes Police a spatial-resource manager: barriers must squeeze the Thief without accidentally cutting off Police's own reachable cells, since a placed barrier is irreversible for the rest of the game (`GAME-007`).

Scoring is asymmetric by design, not a binary win/lose: every terminal outcome pays both sides differently, and a technical loss zeros both sides regardless of position (`GAME-013`) — so protocol correctness is worth more than winning on the clock alone. `docs/decisions/ADR-001-shared-game-contract-shape.md` records the negotiated (non-official) shape of the contract file that carries these values, and `docs/spec/OPEN_QUESTIONS.md` OPEN-011 tracks the one unresolved ambiguity in the terminal-condition rules (whether the move cap and survival threshold are one event or two).

### FastMCP and orchestration dilemmas

The planned solution uses symmetric server/client peers, an explicit lifecycle state machine, immutable request deadlines, bounded retry, and audit evidence. `TODO_BEFORE_SUBMISSION`: document the implemented tool surface, public-connectivity procedure, failure handling, and measured interoperability evidence after OPEN-001/OPEN-007 are resolved.

### Implemented strategy

`TODO_BEFORE_SUBMISSION`: describe only the Police strategy actually implemented and tested. Do not claim reinforcement learning. Add learning curves only if RL is genuinely used and its experiment is reproducible.

### Live GUI evidence

`TODO_BEFORE_SUBMISSION`: insert a real screenshot showing local truth and the opponent-belief heatmap without revealing objective opponent position.

### Replay evidence

`TODO_BEFORE_SUBMISSION`: insert a real Replay screenshot showing per-step `Verified OK` from a verified final log. Never manufacture a screenshot or edit a status into one.

## Testing and quality gates

Local and CI checks use the same three command groups:

```sh
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
```

The quality configuration enforces Ruff zero, 85% global coverage, a 150 logical-code-line limit, required docs, task-ID/TODO consistency, local Markdown links, secret/archive protection, documentation-language hygiene, and least-privilege workflow permissions.

Verification proceeds as a ladder — deterministic unit and golden-vector tests, a local two-process protocol smoke test, a full practice series, artifact validation, network readiness, an uncounted external game, and only then a counted game. The stages, their owning tasks, and their gates are recorded in `docs/PLAN.md`.

## Troubleshooting

- **Task cannot start:** inspect `depends_on` in its task file and the status of each prerequisite in `docs/TODO.md`.
- **Contract/config mismatch:** stop before Step 0; compare only the approved shared terms and record the exact mismatch without secrets.
- **Request timeout:** retain the original deadline, apply bounded configured retry, and preserve failure evidence.
- **Audit mismatch:** do not repair history; preserve the received commitment and revealed record and follow the TAMPERED path.
- **Gmail/OAuth issue:** do not broaden scopes or commit credential files; use mocks until the human live-send gate.
- **Optional provider timeout, 429, or budget limit:** preserve the already selected legal move, fall back to deterministic template text, and never make a live provider call from CI.
- `TODO_BEFORE_SUBMISSION`: add observed platform-specific failures and verified remedies.

## Contributing

Read `CONTRIBUTING.md` and `AGENTS.md`. Claim exactly one ready task, use its write set, run its verification, and hand off structured evidence. GitHub Issues and Pull Requests assist review but never replace the Markdown task graph.

## License and credits

`TODO_BEFORE_SUBMISSION`: the team must choose and document the repository license and credits policy before release. Do not add a license notice or an attribution without verifying what is actually distributed and legally required — and never remove one that is.
