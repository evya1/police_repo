"""Shared fakes and builders for the Gmail composition integration tests."""

from __future__ import annotations

import base64
import json
import threading
import time
from email import policy
from email.parser import BytesParser
from pathlib import Path

from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_documents import build_result, official_final_result
from common.transport.kit_names import result_name
from common.transport.kit_settlement import series_final


class GatekeeperSpy:
    def __init__(self) -> None:
        self.lanes: list[str] = []

    def execute(self, call, *args, **kwargs):
        self.lanes.append(kwargs.get("lane", "reporting"))
        return call(*args, **kwargs)


class Messages:
    def __init__(self) -> None:
        self.body: dict[str, str] | None = None
        self.calls = 0

    def send(self, *, userId: str, body: dict[str, str]):  # noqa: N803
        assert userId == "me"
        self.body = body
        return self

    def execute(self) -> dict[str, str]:
        self.calls += 1
        return {"id": "provider-id-not-persisted"}


class Service:
    def __init__(self) -> None:
        self.resource = Messages()

    def users(self):
        return self

    def messages(self):
        return self.resource


class SlowMessages(Messages):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self._lock = threading.Lock()

    def execute(self) -> dict[str, str]:
        with self._lock:
            self.calls += 1
        time.sleep(0.1)
        return {"id": "one-provider-id"}


class SlowService(Service):
    def __init__(self) -> None:
        self.resource = SlowMessages()


class FailOnceMessages(Messages):
    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def execute(self) -> dict[str, str]:
        self.attempts += 1
        if self.attempts == 1:
            return {}
        return {"id": "retry-provider-id"}


class FailOnceService(Service):
    def __init__(self) -> None:
        self.resource = FailOnceMessages()


class DropResponseOnceMessages(Messages):
    """Gmail may have accepted; the response is lost mid-flight."""

    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def execute(self) -> dict[str, str]:
        self.attempts += 1
        # Transient-looking wording: proves the Gatekeeper must not retry even
        # when the raw provider failure looks retryable, because the outcome
        # of a possibly-started transmission is unknown.
        raise ConnectionError("connection reset after the provider rate window accepted it")


class DropResponseOnceService(Service):
    def __init__(self) -> None:
        self.resource = DropResponseOnceMessages()


class PreSendFailOnceService:
    """Client construction fails once before any request object is built."""

    def __init__(self) -> None:
        self.resource = Messages()
        self.failed = False

    def users(self):
        if not self.failed:
            self.failed = True
            raise RuntimeError("client construction failed before transmission")
        return self

    def messages(self):
        return self.resource


def published_result(root: Path, *, confirmed: bool = True) -> tuple[Path, dict]:
    game_id, game_uid = "group-a-vs-group-b", "00000000-0000-0000-0000-000000000001"
    groups = ("group-a", "group-b")
    rows = [
        {
            "sub_game_number": number,
            "roles": {groups[0]: "police", groups[1]: "thief"},
            "result": "capture",
            "winner_group": groups[0],
            "tie": False,
            "started_at": f"2026-08-26T12:{number:02d}:00+03:00",
            "ended_at": f"2026-08-26T12:{number:02d}:01+03:00",
            "github_commit": {groups[0]: "a" * 40, groups[1]: "b" * 40},
            "tokens": {groups[0]: 0, groups[1]: 0},
            "score": {groups[0]: 100, groups[1]: 0},
            "log_files": dict.fromkeys(groups, f"log_{game_id}_g{number:02d}.json"),
            "audit": {"log_verified": True, "tampered": False},
        }
        for number in range(1, 7)
    ]
    final = official_final_result(series_final(rows, groups, counted=True))
    agreement = mutual_agreement(game_id, final, rows, confirmed=confirmed)
    document = build_result(
        game_id=game_id, game_uid=game_uid, groups=list(groups), sub_games=rows,
        final_result=final, mutual_agreement=agreement,
    )
    path = root / result_name(game_id)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path, document


def parse_message(raw: str):
    return BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
