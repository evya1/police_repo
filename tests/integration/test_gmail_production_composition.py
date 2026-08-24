from __future__ import annotations

import base64
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from common.config import ConfigError
from common.transport.canonical import canonical_bytes
from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_documents import build_result
from common.transport.kit_names import result_name
from common.transport.kit_settlement import series_final
from police_peer.reporting.gmail import DuplicateSendError
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import EmailSettings


class _GatekeeperSpy:
    def __init__(self) -> None:
        self.lanes: list[str] = []

    def execute(self, call, *args, **kwargs):
        self.lanes.append(kwargs.get("lane", "reporting"))
        return call(*args, **kwargs)


class _Messages:
    def __init__(self) -> None:
        self.body: dict[str, str] | None = None

    def send(self, *, userId: str, body: dict[str, str]):  # noqa: N803
        assert userId == "me"
        self.body = body
        return self

    def execute(self) -> dict[str, str]:
        return {"id": "provider-id-not-persisted"}


class _Service:
    def __init__(self) -> None:
        self.resource = _Messages()

    def users(self):
        return self

    def messages(self):
        return self.resource


def _published_result(root: Path, *, confirmed: bool = True) -> tuple[Path, dict]:
    game_id, game_uid = "group-a-vs-group-b", "00000000-0000-0000-0000-000000000001"
    groups = ("group-a", "group-b")
    rows = [
        {
            "sub_game_number": number,
            "roles": {groups[0]: "police", groups[1]: "thief"},
            "result": "capture",
            "winner_group": groups[0],
            "tie": False,
            "steps": 1,
            "tokens": {groups[0]: 0, groups[1]: 0},
            "score": {groups[0]: 100, groups[1]: 0},
            "log_files": {groups[0]: f"log_{game_id}_g{number:02d}.json"},
            "audit": {"log_verified": True, "tampered": False},
        }
        for number in range(1, 7)
    ]
    final = series_final(rows, groups, counted=True)
    agreement = mutual_agreement(game_id, final, rows, confirmed=confirmed)
    document = build_result(
        game_id=game_id, game_uid=game_uid, groups=list(groups), sub_games=rows,
        final_result=final, mutual_agreement=agreement,
    )
    path = root / result_name(game_id)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path, document


def _message(raw: str):
    return BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))


def test_dry_run_uses_friend_sender_and_writes_local_outbox(tmp_path: Path) -> None:
    path, document = _published_result(tmp_path)
    gatekeeper = _GatekeeperSpy()
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), tmp_path, gatekeeper,
    )
    receipt = reporter.report(path)
    outbox = tmp_path / "outbox" / document["game_uid"]
    message = BytesParser(policy=policy.default).parsebytes((outbox / "message.eml").read_bytes())
    (attachment,) = message.iter_attachments()
    assert attachment.get_filename() == path.name
    assert attachment.get_payload(decode=True) == canonical_bytes(document)
    assert receipt.gmail_api_contacted is False
    assert gatekeeper.lanes == ["reporting"]
    assert "recipient" not in (outbox / "receipt.json").read_text(encoding="utf-8")


def test_live_mode_reaches_gmail_compatible_client_once(tmp_path: Path) -> None:
    path, _ = _published_result(tmp_path)
    gatekeeper, service = _GatekeeperSpy(), _Service()
    reporter = compose_gmail_reporter(
        EmailSettings("placeholder@example.com", "send"), tmp_path, gatekeeper,
        recipient="recipient@example.invalid", authorize_send=True,
        environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        service_client=service,
    )
    receipt = reporter.report(path)
    message = _message(service.resource.body["raw"])
    assert message["To"] == "recipient@example.invalid"
    assert receipt.gmail_api_contacted is True
    assert gatekeeper.lanes == ["reporting"]
    with pytest.raises(DuplicateSendError):
        reporter.report(path)


def test_send_requires_authorization_and_confirmed_result(tmp_path: Path) -> None:
    path, _ = _published_result(tmp_path, confirmed=False)
    with pytest.raises(ConfigError, match="authorize"):
        compose_gmail_reporter(
            EmailSettings("recipient@example.invalid", "send"), tmp_path, _GatekeeperSpy(),
            environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        )
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), tmp_path, _GatekeeperSpy(),
    )
    with pytest.raises(ConfigError, match="agreement"):
        reporter.report(path)
