# Police peer CLI

The CLI starts this repository's Police peer as an MCP server, connects it to one peer, and
runs a six-sub-game series. Its implementation is `police_peer.cli`; orchestration is delegated
to `police_peer.runner`, and peer construction is delegated to `police_peer.sdk`.

## Installation and entry points

Install the locked project and development dependencies from the repository root:

```sh
uv sync --locked --all-groups
```

The installed console scripts are equivalent:

```sh
uv run police-peer --help
uv run police_peer --help
uv run python -m police_peer --help
```

## Local warm-up

Install both repositories, then start the peers in separate terminals. The defaults are paired
for loopback networking:

```sh
# police_repo
uv run police-peer --artifacts-dir artifacts/police-warmup
```

```sh
# thief_repo
uv run thief-peer --artifacts-dir artifacts/thief-warmup
```

Each process serves its own MCP endpoint, connects to the other endpoint, and runs the series.
Omit `--artifacts-dir` when no files should be written.

## Remote peer

Set the actual bind address and opponent URL with CLI network flags:

```sh
uv run police-peer \
  --listen-host 0.0.0.0 \
  --listen-port 8101 \
  --peer-url https://thief.example/mcp \
  --public-url https://police.example/mcp
```

`--listen-host`, `--listen-port`, and `--peer-url` control actual networking. `--public-url`
only declares this peer's externally reachable MCP URL in identity metadata; it does not create
a tunnel, configure routing, or change the listening socket. Establish the public route before
starting the peer.

## Options

These are all options created by `build_parser()`:

| Option | Type or values | Exact default | Behavior |
| --- | --- | --- | --- |
| `-h`, `--help` | flag | n/a | Print help and exit. |
| `--listen-host` | string | `"127.0.0.1"` | FastMCP server bind host. |
| `--listen-port` | integer | `8101` | FastMCP server bind port. |
| `--peer-url` | string | `"http://127.0.0.1:8102/mcp"` | Opponent MCP URL used for readiness checks and the client channel. |
| `--shared-config` | path | `"config/game.json"` | Shared game JSON. |
| `--private-config` | path | `None` | Optional private TOML. |
| `--group-id` | string | `"police-local"` | Runtime peer/group identifier. |
| `--mode` | `warmup`, `counted`, `competition`, `live` | `"warmup"` | Series mode label and safeguard selector. |
| `--artifacts-dir` | path | `None` | Enables artifact writing in this directory. |
| `--seed` | integer | `0` | Random seed; zero allows a private-config seed to be used. |
| `--connect-timeout` | float, seconds | `30.0` | Maximum time spent waiting for the peer URL to answer. |
| `--turn-timeout` | float, seconds | `30.0` | MCP operation and settlement budget. |
| `--wire-profile` | `internal`, `reference-v3` | `"reference-v3"` | Opponent audit-wire shape. `reference-v3` is the pinned league-kit lane. |
| `--emit-kit-bundle`, `--no-emit-kit-bundle` | boolean flag pair | `True` | Enable or disable the league-kit projection when artifacts are enabled. |
| `--group-code-confirmed` | flag | `False` | Assert human confirmation of the configured eight-character team code for counted play. |
| `--public-url` | string | `""` | Override `[network].public_url` in declaration metadata when nonempty. |

## Mode behavior

All four accepted modes start the same server/client transport and attempt the same six-sub-game
series and settlement flow.

| Mode | Reachable behavior |
| --- | --- |
| `warmup` | Uncounted run. Missing declaration identity is tolerated. |
| `counted` | Runs counted readiness before transport starts and fails closed if it is incomplete. After play, lack of result agreement returns exit code `6`. |
| `competition` | Currently follows the same uncounted runtime path as `warmup`; it has no distinct counted semantics. |
| `live` | Currently follows the same uncounted runtime path as `warmup`; it has no distinct counted semantics. It does not start a distinct Live GUI path. |

Only `counted` activates counted safeguards. The other mode strings are still passed through to
the SDK and recorded in the summary artifact when artifacts are enabled.

## Post-series settlement

In every mode the runner settles the series after the six sub-games. When the series never
settled there is nothing to agree and the step returns immediately. Otherwise the runner sends
this peer's proposal once over the control lane and then waits up to `--turn-timeout` for the
opponent's proposal. The wait never raises: a played, audited series is not lost to a quiet
opponent.

Two consequences for an operator:

- The process stays alive for up to one full `--turn-timeout` after the last sub-game. Against
  a peer that never answers the control lane (the reference kit is one such peer), the wait
  always runs to the deadline.
- When the opponent's proposal never arrives, the emitted kit bundle records
  `mutual_agreement.confirmed: false` — `confirmed` is never assumed. In uncounted modes this
  does not change the exit code; only `counted` turns a missing agreement into exit code `6`.

## Running against the reference kit

The pinned `copthief-league-protocol` kit speaks the `reference-v3` wire lane, which is already
this CLI's default, so no special flags are needed for kit interop. When you want the invocation
to say what it means, the kit-compatibility combination is:

```sh
uv run police_peer \
  --mode warmup \
  --wire-profile reference-v3 \
  --emit-kit-bundle \
  --artifacts-dir artifacts/police-kit
```

- `--mode warmup` — the kit is an uncounted sparring peer. `counted` would add the readiness
  gate and the agreement exit-code check against a peer that never confirms settlement.
- `--wire-profile reference-v3` — the kit's nested audit envelope. Pass `internal` only for a
  peer that speaks this project's own flat audit shape.
- `--emit-kit-bundle` — emit the league-kit projection beside the internal replay bundle.

Expected honest outcomes against the kit: the six sub-games play clean, the settlement wait
runs the full `--turn-timeout`, the kit bundle records `confirmed: false`, and the process
still exits `0` in warmup.

## Configuration precedence

OpenRouter's configuration, Python API, request/response fields, fallback behavior, token
accounting, and safe test commands are documented in [OpenRouter hint-wording API](OPENROUTER.md).

- CLI path flags select the shared JSON and optional private TOML. There is no environment-variable
  configuration layer in `cli.py`.
- Shared JSON supplies the negotiated game terms and wins over conflicting private TOML values;
  private TOML can supply local-only settings. The runner always enforces six sub-games.
- A nonzero `--seed` wins over the private seed. The CLI default `0` defers to the private seed,
  or remains zero when no private seed is present.
- CLI listen, peer URL, connect-timeout, and turn-timeout values—including their parser defaults—
  are passed directly to the runner. Private `[network]` endpoint values do not configure the
  actual CLI sockets or peer connection.
- A nonempty `--public-url` wins over private `[network].public_url`; an empty value defers to the
  private value. This affects declaration metadata only.
- `--group-id` is the runtime identity. In counted mode it must equal `[game].group_id` from the
  private TOML.

## Counted-mode prerequisites

Config loading happens in every mode, before the counted gate: a missing or invalid
`--shared-config`, or a `--private-config` that cannot be loaded, raises an uncaught startup
error — a traceback and the normal Python process failure code — before the MCP server starts.

Once loading succeeds, `--mode counted` refuses before any transport starts and returns `2`,
naming the missing item, when:

- `--group-code-confirmed` is not passed;
- the private declaration is incomplete: `[game].group_id` missing or different from
  `--group-id`, empty group name or members, missing `cop` or `thief` repository URLs, an empty
  LLM model, or no public MCP URL from `--public-url` or `[network].public_url`;
- the 40-character commit at this repository's `HEAD` cannot be resolved (read straight from
  `.git`, so an exported tarball refuses);
- runtime hardware metadata or the pairing-history count cannot form the identity declaration;
- the negotiated terms are empty, so no configuration digest can be computed; or
- the attached token ledger records unknown counted usage.

## Runner exit codes

`main()` returns the integer returned by `run_one_peer()`:

| Code | Meaning |
| --- | --- |
| `0` | The series result settled. For uncounted modes, a separate settlement-agreement failure does not change this code. |
| `1` | Series execution raised an exception inside the runner's execution boundary. An uncaught startup/configuration exception also produces the normal Python process failure code. |
| `2` | Counted readiness failed before transport startup. `argparse` also independently uses process status `2` for invalid CLI syntax. |
| `6` | The series did not settle, or a counted series lacked result agreement. |
| `7` | The peer URL did not answer before `--connect-timeout`. |

## Artifacts and Gmail

Artifact writing is disabled unless `--artifacts-dir` is provided. When enabled, the runner
writes the JSON series summary to `<artifacts-dir>/result_<game_id>.json`. For a settled result
it also publishes the internal replay bundle under `<artifacts-dir>/replay/<game_uid>/`; with
the default `--emit-kit-bundle`, it additionally attempts the league-kit projection under
`<artifacts-dir>/kit/<game_uid>/`. `--no-emit-kit-bundle` disables only that projection. A kit
projection failure is logged and is nonfatal; summary or internal-bundle write failures are not
given that nonfatal boundary — they raise into the runner's execution boundary and produce exit
code `1`.

The CLI does not send Gmail, in any mode. It only runs the peer and optionally writes local
artifacts. Gmail sending belongs to a separate reporting pipeline and is not invoked by
`police_peer.cli` or `police_peer.runner`.

## Python API and boundary

```python
from police_peer.cli import build_parser, main

parser = build_parser()  # -> argparse.ArgumentParser
status = main(["--mode", "warmup"])  # -> int
```

- `build_parser() -> argparse.ArgumentParser` constructs the parser without parsing arguments.
- `main(argv: list[str] | None = None) -> int` parses the supplied list, or `sys.argv` when it is
  `None`, converts path arguments to `pathlib.Path`, fixes the natural role to Police, and returns
  the peer runner's status.

The boundary is intentionally short: CLI parsing and type conversion → runner process lifecycle,
networking, settlement, and optional artifacts → SDK configuration validation and peer/strategy
composition. Game and protocol behavior remains below the SDK boundary.
