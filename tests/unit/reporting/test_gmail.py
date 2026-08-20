from __future__ import annotations

import pytest

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import (
    AttachmentMissingError,
    DraftSubstitutionError,
    DuplicateSendError,
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

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"])

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(["https://www.googleapis.com/auth/gmail.compose"])


def test_gmail_sender_scope_validation_in_constructor() -> None:
    gk = ExternalApiGatekeeper()
    # Valid scope passes
    sender = GmailSender(gatekeeper=gk, scopes=["https://www.googleapis.com/auth/gmail.send"])
    assert sender.scopes == ["https://www.googleapis.com/auth/gmail.send"]

    # Invalid scope raises InvalidScopeError
    with pytest.raises(InvalidScopeError):
        GmailSender(gatekeeper=gk, scopes=["https://www.googleapis.com/auth/gmail.readonly"])


def test_gmail_sender_recipient_handling() -> None:
    gk = ExternalApiGatekeeper()
    sender = GmailSender(gatekeeper=gk)
    artifacts = [("report.json", b'{"result": 1}')]

    # Without default or explicit recipient -> raises ValueError
    with pytest.raises(ValueError, match="Recipient email address must be explicitly provided"):
        sender.send_report(game_uid="g-no-recip", artifacts=artifacts)

    # With explicit recipient -> succeeds
    res = sender.send_report(game_uid="g-explicit", artifacts=artifacts, recipient="eval@example.org")
    assert res["status"] == "SENT"

    # With configured default recipient -> succeeds
    configured_sender = GmailSender(gatekeeper=gk, default_recipient="league@example.org")
    res2 = configured_sender.send_report(game_uid="g-default", artifacts=artifacts)
    assert res2["status"] == "SENT"


def test_gmail_sender_fake_client_send() -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="messages")
    sender = GmailSender(gatekeeper=gk, default_recipient="test@example.com", service_client=client)

    res = sender.send_report(
        game_uid="game-100",
        artifacts=[("decl.json", b'{"kind": "decl"}')],
    )
    assert res["status"] == "OK"


def test_gmail_sender_draft_substitution_refused() -> None:
    gk = ExternalApiGatekeeper()
    client = FakeGmailService(mode="drafts")
    sender = GmailSender(gatekeeper=gk, default_recipient="test@example.com", service_client=client)

    with pytest.raises(DraftSubstitutionError):
        sender.send_report(
            game_uid="game-101",
            artifacts=[("decl.json", b'{"kind": "decl"}')],
        )


def test_gmail_sender_empty_attachment_refused() -> None:
    gk = ExternalApiGatekeeper()
    sender = GmailSender(gatekeeper=gk, default_recipient="test@example.com")

    with pytest.raises(AttachmentMissingError):
        sender.send_report(game_uid="game-102", artifacts=[])

    with pytest.raises(AttachmentMissingError):
        sender.send_report(game_uid="game-103", artifacts=[("f.json", b"")])


def test_gmail_sender_duplicate_send_refused() -> None:
    gk = ExternalApiGatekeeper()
    sender = GmailSender(gatekeeper=gk, default_recipient="test@example.com")
    artifacts = [("decl.json", b'{"kind": "decl"}')]

    sender.send_report(game_uid="game-dup", artifacts=artifacts)
    with pytest.raises(DuplicateSendError):
        sender.send_report(game_uid="game-dup", artifacts=artifacts)
