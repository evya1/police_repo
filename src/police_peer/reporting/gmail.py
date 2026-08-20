from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailError(Exception):
    """Base error for Gmail reporting operations."""


class InvalidScopeError(GmailError):
    """Raised when OAuth scope broader than gmail.send is requested or granted."""


class AttachmentMissingError(GmailError):
    """Raised when required JSON artifact attachments are missing."""


class DraftSubstitutionError(GmailError):
    """Raised when draft creation is attempted instead of mandatory send."""


class DuplicateSendError(GmailError):
    """Raised when attempting to resend an already-reported series result."""


def validate_oauth_scope(scopes: list[str] | str) -> None:
    scope_list = [scopes] if isinstance(scopes, str) else list(scopes)
    for scope in scope_list:
        normalized = scope.strip()
        if normalized not in (GMAIL_SEND_SCOPE, "gmail.send"):
            raise InvalidScopeError(f"Unauthorized OAuth scope '{normalized}'. Only gmail.send is permitted.")


def build_email_message(
    *,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]],
) -> tuple[EmailMessage, str]:
    if not attachments:
        raise AttachmentMissingError("Email report must contain at least one JSON artifact attachment.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    for filename, data in attachments:
        if not data:
            raise AttachmentMissingError(f"Attachment {filename} is empty.")
        msg.add_attachment(data, maintype="application", subtype="json", filename=filename)

    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii")
    return msg, raw_b64


class GmailSender:
    """Send-only Gmail adapter routed strictly through the central Gatekeeper."""

    def __init__(
        self,
        gatekeeper: ExternalApiGatekeeper,
        sender_email: str = "peer@local",
        default_recipient: str | None = None,
        scopes: list[str] | str | None = None,
        service_client: Any = None,
    ) -> None:
        if scopes is not None:
            validate_oauth_scope(scopes)
        self.gatekeeper = gatekeeper
        self.sender_email = sender_email
        self.default_recipient = default_recipient
        self.scopes = [scopes] if isinstance(scopes, str) else list(scopes or [])
        self._client = service_client
        self._sent_game_uids: set[str] = set()

    def send_report(
        self,
        *,
        game_uid: str,
        artifacts: list[tuple[str, bytes]],
        recipient: str | None = None,
        subject: str | None = None,
        body: str = "Automated Police/Thief series report attached.",
    ) -> dict[str, Any]:
        if game_uid in self._sent_game_uids:
            raise DuplicateSendError(f"Report for game_uid '{game_uid}' has already been transmitted.")

        target_recipient = recipient or self.default_recipient
        if not target_recipient:
            raise ValueError("Recipient email address must be explicitly provided or configured.")

        target_subject = subject or f"[PoliceThief-Report] Series {game_uid}"

        _, raw_b64 = build_email_message(
            sender=self.sender_email,
            recipient=target_recipient,
            subject=target_subject,
            body=body,
            attachments=artifacts,
        )

        def _raw_send() -> dict[str, Any]:
            if self._client is not None:
                # Disallow draft substitutions
                users_res = self._client.users() if hasattr(self._client, "users") else self._client
                if not hasattr(users_res, "messages"):
                    raise DraftSubstitutionError("Cannot use drafts API for report transmission.")
                try:
                    messages_res = users_res.messages()
                except Exception as exc:
                    raise DraftSubstitutionError("Cannot use drafts API for report transmission.") from exc
                return messages_res.send(userId="me", body={"raw": raw_b64}).execute()
            # Fake transmission receipt for testing when client is not injected
            return {"id": f"msg-{game_uid}", "status": "SENT", "raw_length": len(raw_b64)}

        result = self.gatekeeper.execute(_raw_send)
        self._sent_game_uids.add(game_uid)
        return result
