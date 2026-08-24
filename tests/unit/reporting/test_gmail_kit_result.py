from __future__ import annotations

import base64
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from common.transport.canonical import canonical_bytes
from common.transport.kit_names import result_name
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import (
    DuplicateSendError,
    FileIdempotencyStore,
    GmailClientNotConfiguredError,
    GmailSender,
)


class FakeMessagesResource:
    def __init__(self) -> None:
        self.request: tuple | None = None

    def send(self, userId: str, body: dict) -> FakeMessagesResource:  # noqa: N803
        self.request = (userId, body)
        return self

    def execute(self) -> dict:
        return {"id": "12345", "status": "OK"}


class FakeGmailService:
    def __init__(self) -> None:
        self.resource = FakeMessagesResource()

    def users(self) -> FakeGmailService:
        return self

    def messages(self) -> FakeMessagesResource:
        return self.resource


def _make(tmp_path: Path, *, client=None) -> GmailSender:
    return GmailSender(
        gatekeeper=ExternalApiGatekeeper(),
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="recipient@example.invalid",
        service_client=client,
        idempotency_store=FileIdempotencyStore(tmp_path / "sent.json"),
    )


def _result(game_id: str = "team-a-vs-team-b") -> dict:
    return {
        "schema_version": "1.1",
        "report_type": "final_game_result",
        "game_id": game_id,
        "game_uid": "da4f6f1e-0000-0000-0000-000000000000",
        "groups": ["team-a", "team-b"],
        "num_sub_games": 6,
        "sub_games": [],
        "final_result": {"total_score": {"team-a": 100, "team-b": 40}},
    }


def _decode(raw_b64: str):
    raw = base64.urlsafe_b64decode(raw_b64)
    return BytesParser(policy=policy.default).parsebytes(raw)


def test_body_is_the_exact_canonical_compact_bytes(tmp_path: Path) -> None:
    client = FakeGmailService()
    sender = _make(tmp_path, client=client)
    result = _result()
    sender.send_kit_result(game_uid=result["game_uid"], result=result)

    raw = client.resource.request[1]["raw"]
    msg = _decode(raw)
    # The text body must be the canonical COMPACT form -- never a pretty-printed
    # re-serialization (SPEC §6, WARNINGS §6). ``EmailMessage`` appends a trailing newline,
    # which is accepted.
    expected = canonical_bytes(result).decode("utf-8") + "\n"
    assert msg.get_body(preferencelist=("plain",)).get_content() == expected


def test_single_named_attachment_is_the_same_file(tmp_path: Path) -> None:
    client = FakeGmailService()
    sender = _make(tmp_path, client=client)
    result = _result()
    sender.send_kit_result(game_uid=result["game_uid"], result=result)

    raw = client.resource.request[1]["raw"]
    msg = _decode(raw)
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1, "the kit email carries exactly one attachment"
    attachment = attachments[0]
    assert attachment.get_filename() == result_name(result["game_id"])
    assert attachment.get_payload(decode=True) == canonical_bytes(result)


def test_attachment_filename_falls_back_to_result_name(tmp_path: Path) -> None:
    client = FakeGmailService()
    sender = _make(tmp_path, client=client)
    result = _result()
    sender.send_kit_result(game_uid=result["game_uid"], result=result)
    raw = client.resource.request[1]["raw"]
    msg = _decode(raw)
    (attachment,) = msg.iter_attachments()
    assert attachment.get_filename() == f"result_{result['game_id']}.json"


def test_duplicate_send_refused(tmp_path: Path) -> None:
    client = FakeGmailService()
    sender = _make(tmp_path, client=client)
    result = _result()
    sender.send_kit_result(game_uid=result["game_uid"], result=result)
    with pytest.raises(DuplicateSendError):
        sender.send_kit_result(game_uid=result["game_uid"], result=result)


def test_missing_client_raises(tmp_path: Path) -> None:
    sender = _make(tmp_path, client=None)
    with pytest.raises(GmailClientNotConfiguredError):
        sender.send_kit_result(game_uid="g", result=_result())


def test_missing_recipient_raises(tmp_path: Path) -> None:
    client = FakeGmailService()
    sender = GmailSender(
        gatekeeper=ExternalApiGatekeeper(),
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        service_client=client,
        idempotency_store=FileIdempotencyStore(tmp_path / "sent.json"),
    )
    with pytest.raises(ValueError, match="Recipient email address must be explicitly provided"):
        sender.send_kit_result(game_uid="g", result=_result())
