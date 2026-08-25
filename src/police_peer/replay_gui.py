"""Repository-native adapter from league-kit logs to the Tk Replay GUI facade."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from common.transport.canonical import commit


class ReplayGuiError(ValueError):
    """Raised when a compatible, intact replay log cannot be selected."""


@dataclass(frozen=True)
class ReplayData:
    log_path: Path
    game_id: str
    role: str
    result: str
    winner: str
    board_size: int
    own_records: list[dict]
    opponent_records: list[dict]
    audit_passed: bool


def resolve_log(source: Path | str) -> Path:
    """Resolve one log directly or select the first sub-game in a bundle directory."""
    path = Path(source).expanduser().resolve()
    if path.is_file() and path.suffix.lower() == ".json":
        return path
    if path.is_dir():
        logs = sorted(path.rglob("log_*_g*.json"))
        if logs:
            return logs[0]
    raise ReplayGuiError(f"no compatible log_<game_id>_g<NN>.json found at {path}")


def _verify_half(records: list[dict], label: str) -> list[str]:
    problems = []
    for index, record in enumerate(records):
        try:
            reproduced = commit(record["payload"], record["nonce"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"{label}[{index}] is malformed")
            continue
        if reproduced != record.get("commit"):
            problems.append(f"{label}[{index}] commitment mismatch")
    return problems


def verify_replay_log(source: Path | str) -> tuple[bool, str]:
    """Re-hash both sealed halves before any replay state is displayed."""
    path = resolve_log(source)
    document = json.loads(path.read_text(encoding="utf-8"))
    own = document.get("records") or []
    opponent = document.get("opponent_records") or []
    if not own or not opponent:
        return False, f"{path.name}: TAMPERED — both sealed halves are required"
    problems = _verify_half(own, "records") + _verify_half(opponent, "opponent_records")
    if problems:
        return False, f"{path.name}: TAMPERED — {'; '.join(problems[:4])}"
    return True, (
        f"{path.name}: Verified OK — {len(own) + len(opponent)} records re-hashed "
        "against their commitments (both halves)"
    )


def _board_size(path: Path) -> int:
    config = path.with_name(path.name.replace("log_", "config_", 1))
    if config.is_file():
        document = json.loads(config.read_text(encoding="utf-8"))
        size = document.get("terms", {}).get("board_size")
        if isinstance(size, int) and size > 0:
            return size
    return 7


def load_replay(source: Path | str) -> ReplayData:
    path = resolve_log(source)
    document = json.loads(path.read_text(encoding="utf-8"))
    summary = document.get("summary") or {}
    return ReplayData(
        log_path=path,
        game_id=str(document.get("game_id", "unknown")),
        role=str(summary.get("role", "peer")),
        result=str(summary.get("result", "unknown")),
        winner=str(summary.get("winner_group", "unknown")),
        board_size=_board_size(path),
        own_records=list(document.get("records") or []),
        opponent_records=list(document.get("opponent_records") or []),
        audit_passed=bool((summary.get("audit") or {}).get("passed")),
    )


def launch_replay_gui(source: Path | str, *, config_dir: Path | str = "config") -> int:
    """Verify both halves, then open the repository-native Tk replay facade."""
    del config_dir  # Reserved for a future live-view configuration adapter.
    ok, report = verify_replay_log(source)
    print(report, flush=True)
    if not ok:
        return 6
    from police_peer.replay_gui_window import ReplayWindow

    ReplayWindow(load_replay(source), report).run()
    return 0
