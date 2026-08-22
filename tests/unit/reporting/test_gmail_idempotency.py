from __future__ import annotations

from pathlib import Path

import pytest

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import (
    AttachmentMissingError,
    DraftSubstitutionError,
    DuplicateSendError,
    FileIdempotencyStore,
    GmailSender,
)


class FakeGmailService:
    def __init__(self, mode: str = "messages") -> None:
        self.mode = mode

    def users(self) -> FakeGmailService:
        return self

    def messages(self) -> FakeMessagesResource:
        if self.mode == "drafts":
            raise AttributeError("drafts resource only")
        return FakeMessagesResource()

    def drafts(self) -> FakeMessagesResource:
        return FakeMessagesResource()


class FakeMessagesResource:
    def send(self, userId: str, body: dict) -> FakeMessagesResource:  # noqa: N803
        return self

    def execute(self) -> dict:
        return {"id": "12345", "status": "OK"}


def test_durable_idempotency(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="messages")
    store_file = tmp_path / "custom_sent.json"

    store1 = FileIdempotencyStore(store_file)
    sender1 = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=client,
        idempotency_store=store1,
    )
    artifacts = [("decl.json", b'{"kind": "decl"}')]

    res = sender1.send_report(game_uid="game-durable-1", artifacts=artifacts)
    assert res["status"] == "OK"

    store2 = FileIdempotencyStore(store_file)
    sender2 = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=client,
        idempotency_store=store2,
    )

    with pytest.raises(DuplicateSendError):
        sender2.send_report(game_uid="game-durable-1", artifacts=artifacts)


def test_draft_substitution_refused(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="drafts")
    store = FileIdempotencyStore(tmp_path / "sent.json")
    sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=client,
        idempotency_store=store,
    )

    with pytest.raises(DraftSubstitutionError):
        sender.send_report(
            game_uid="game-101",
            artifacts=[("decl.json", b'{"kind": "decl"}')],
        )


def test_empty_attachment_refused(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="messages")
    store = FileIdempotencyStore(tmp_path / "sent.json")
    sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=client,
        idempotency_store=store,
    )

    with pytest.raises(AttachmentMissingError):
        sender.send_report(game_uid="game-102", artifacts=[])

    with pytest.raises(AttachmentMissingError):
        sender.send_report(game_uid="game-103", artifacts=[("f.json", b"")])


def test_duplicate_send_refused(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="messages")
    store = FileIdempotencyStore(tmp_path / "sent.json")
    sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=client,
        idempotency_store=store,
    )
    artifacts = [("decl.json", b'{"kind": "decl"}')]

    sender.send_report(game_uid="game-dup", artifacts=artifacts)
    with pytest.raises(DuplicateSendError):
        sender.send_report(game_uid="game-dup", artifacts=artifacts)
