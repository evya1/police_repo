import pytest

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import (
    AttachmentMissingError,
    DraftSubstitutionError,
    DuplicateSendError,
    GmailSender,
    InvalidScopeError,
    build_email_message,
    validate_oauth_scope,
)


class FakeGmailClient:
    def __init__(self, is_draft: bool = False) -> None:
        self.is_draft = is_draft
        self.sent_messages = []

    def users(self):
        return self

    def messages(self):
        if self.is_draft:
            raise AttributeError("Draft-only client")
        return self

    def drafts(self):
        return self

    def send(self, userId: str, body: dict):
        self.sent_messages.append((userId, body))
        return self

    def execute(self):
        return {"id": "12345", "status": "OK"}


def test_validate_oauth_scope():
    validate_oauth_scope("https://www.googleapis.com/auth/gmail.send")
    validate_oauth_scope(["gmail.send"])

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope("https://mail.google.com/")

    with pytest.raises(InvalidScopeError):
        validate_oauth_scope(["gmail.send", "gmail.readonly"])


def test_build_email_message_attachments():
    with pytest.raises(AttachmentMissingError):
        build_email_message(
            sender="a@b.com", recipient="c@d.com", subject="S", body="B", attachments=[]
        )

    msg, raw = build_email_message(
        sender="a@b.com", recipient="c@d.com", subject="S", body="B",
        attachments=[("report.json", b'{"result": 1}')]
    )
    assert msg["To"] == "c@d.com"
    assert raw is not None
    assert len(raw) > 0


def test_gmail_sender_workflow_and_idempotence():
    gk = ExternalApiGatekeeper()
    client = FakeGmailClient()
    sender = GmailSender(gatekeeper=gk, service_client=client)

    artifacts = [("decl.json", b'{"kind": "decl"}')]
    res = sender.send_report(game_uid="game-100", artifacts=artifacts)
    assert res["status"] == "OK"
    assert len(client.sent_messages) == 1

    # Duplicate send for same game_uid is blocked
    with pytest.raises(DuplicateSendError):
        sender.send_report(game_uid="game-100", artifacts=artifacts)


def test_draft_substitution_prevented():
    gk = ExternalApiGatekeeper()
    draft_client = FakeGmailClient(is_draft=True)
    sender = GmailSender(gatekeeper=gk, service_client=draft_client)

    with pytest.raises(Exception):
        sender.send_report(game_uid="game-200", artifacts=[("f.json", b"{}")])
