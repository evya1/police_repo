from __future__ import annotations

from typing import Any

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail_support import (
    GMAIL_SEND_SCOPE,
    AttachmentMissingError,
    DraftSubstitutionError,
    DuplicateSendError,
    FileIdempotencyStore,
    GmailClientNotConfiguredError,
    GmailError,
    IdempotencyStore,
    InvalidScopeError,
    build_email_message,
    validate_oauth_scope,
)

__all__ = [
    "GMAIL_SEND_SCOPE", "AttachmentMissingError", "DraftSubstitutionError",
    "DuplicateSendError", "FileIdempotencyStore", "GmailClientNotConfiguredError",
    "GmailError", "GmailSender", "IdempotencyStore", "InvalidScopeError",
    "build_email_message", "validate_oauth_scope",
]


class GmailSender:
    """Send-only Gmail adapter routed strictly through the central Gatekeeper."""

    def __init__(
        self,
        gatekeeper: ExternalApiGatekeeper,
        scopes: list[str] | str | None = None,
        sender_email: str = "peer@local",
        default_recipient: str | None = None,
        service_client: Any = None,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        validate_oauth_scope(scopes)
        self.gatekeeper = gatekeeper
        self.sender_email = sender_email
        self.default_recipient = default_recipient
        self.scopes = [scopes] if isinstance(scopes, str) else list(scopes)  # type: ignore[arg-type]
        self._client = service_client
        self.idempotency_store = idempotency_store if idempotency_store is not None else FileIdempotencyStore()

    def send_report(
        self,
        *,
        game_uid: str,
        artifacts: list[tuple[str, bytes]],
        recipient: str | None = None,
        subject: str | None = None,
        body: str = "Automated Police/Thief series report attached.",
    ) -> dict[str, Any]:
        if self.idempotency_store.is_sent(game_uid):
            raise DuplicateSendError(f"Report for game_uid '{game_uid}' has already been transmitted.")

        if self._client is None:
            raise GmailClientNotConfiguredError("Gmail service client is not configured.")

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
            # Disallow draft substitutions
            users_res = self._client.users() if hasattr(self._client, "users") else self._client
            if not hasattr(users_res, "messages"):
                raise DraftSubstitutionError("Cannot use drafts API for report transmission.")
            try:
                messages_res = users_res.messages()
            except Exception as exc:
                raise DraftSubstitutionError("Cannot use drafts API for report transmission.") from exc
            return messages_res.send(userId="me", body={"raw": raw_b64}).execute()

        result = self.gatekeeper.execute(_raw_send)
        self.idempotency_store.mark_sent(game_uid)
        return result

    def send_kit_result(
        self,
        *,
        game_uid: str,
        result_bytes: bytes,
        filename: str,
        recipient: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """Send the exact already-published result bytes as the single JSON attachment."""
        if self.idempotency_store.is_sent(game_uid):
            raise DuplicateSendError(f"Report for game_uid '{game_uid}' has already been transmitted.")

        if self._client is None:
            raise GmailClientNotConfiguredError("Gmail service client is not configured.")

        target_recipient = recipient or self.default_recipient
        if not target_recipient:
            raise ValueError("Recipient email address must be explicitly provided or configured.")

        target_subject = subject or f"[PoliceThief-Report] Series {game_uid}"
        body = (
            "The validated final Police/Thief series report is attached as JSON. "
            f"Series identifier: {game_uid}."
        )

        _, raw_b64 = build_email_message(
            sender=self.sender_email,
            recipient=target_recipient,
            subject=target_subject,
            body=body,
            attachments=[(filename, result_bytes)],
        )

        def _raw_send() -> dict[str, Any]:
            users_res = self._client.users() if hasattr(self._client, "users") else self._client
            if not hasattr(users_res, "messages"):
                raise DraftSubstitutionError("Cannot use drafts API for report transmission.")
            try:
                messages_res = users_res.messages()
            except Exception as exc:
                raise DraftSubstitutionError("Cannot use drafts API for report transmission.") from exc
            return messages_res.send(userId="me", body={"raw": raw_b64}).execute()

        result_dict = self.gatekeeper.execute(_raw_send)
        self.idempotency_store.mark_sent(game_uid)
        return result_dict
