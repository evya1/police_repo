from __future__ import annotations

from pathlib import Path

import pytest

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import (
    FileIdempotencyStore,
    GmailClientNotConfiguredError,
    GmailSender,
    InvalidScopeError,
    validate_oauth_scope,
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


def test_oauth_scope_validation() -> None:
    validate_oauth_scope(["https://www.googleapis.com/auth/gmail.send"])
    validate_oauth_scope(["gmail.send"])
    validate_oauth_scope("https://www.googleapis.com/auth/gmail.send")

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(
            ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
        )

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(["https://www.googleapis.com/auth/gmail.compose"])

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(None)

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope([])


def test_scope_mandatory() -> None:
    gk = ExternalApiGatekeeper()
    with pytest.raises(InvalidScopeError):
        GmailSender(gatekeeper=gk, scopes=None)

    with pytest.raises(InvalidScopeError):
        GmailSender(gatekeeper=gk, scopes=[])


def test_no_client_raises(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    store = FileIdempotencyStore(tmp_path / "sent.json")
    sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="test@example.com",
        service_client=None,
        idempotency_store=store,
    )
    artifacts = [("decl.json", b'{"kind": "decl"}')]
    with pytest.raises(GmailClientNotConfiguredError):
        sender.send_report(game_uid="game-no-client", artifacts=artifacts)


def test_gmail_sender_scope_validation_in_constructor() -> None:
    gk = ExternalApiGatekeeper()
    sender = GmailSender(gatekeeper=gk, scopes=["https://www.googleapis.com/auth/gmail.send"])
    assert sender.scopes == ["https://www.googleapis.com/auth/gmail.send"]

    with pytest.raises(InvalidScopeError):
        GmailSender(gatekeeper=gk, scopes=["https://www.googleapis.com/auth/gmail.readonly"])


def test_gmail_sender_recipient_handling(tmp_path: Path) -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="messages")
    store = FileIdempotencyStore(tmp_path / "sent.json")
    sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        service_client=client,
        idempotency_store=store,
    )
    artifacts = [("report.json", b'{"result": 1}')]

    with pytest.raises(ValueError, match="Recipient email address must be explicitly provided"):
        sender.send_report(game_uid="g-no-recip", artifacts=artifacts)

    res = sender.send_report(game_uid="g-explicit", artifacts=artifacts, recipient="eval@example.org")
    assert res["status"] == "OK"

    configured_sender = GmailSender(
        gatekeeper=gk,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        default_recipient="league@example.org",
        service_client=client,
        idempotency_store=store,
    )
    res2 = configured_sender.send_report(game_uid="g-default", artifacts=artifacts)
    assert res2["status"] == "OK"


def test_fake_client_send(tmp_path: Path) -> None:
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

    res = sender.send_report(
        game_uid="game-100",
        artifacts=[("decl.json", b'{"kind": "decl"}')],
    )
    assert res["status"] == "OK"
