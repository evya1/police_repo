from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from common.transport.canonical import canonical_bytes
from common.transport.kit_names import result_name
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailError(Exception):
    """Base error for Gmail reporting operations."""


class GmailClientNotConfiguredError(GmailError):
    """Raised when report transmission is attempted without a configured service client."""


class InvalidScopeError(GmailError):
    """Raised when OAuth scope broader than gmail.send is requested or granted, or scope is missing."""


class AttachmentMissingError(GmailError):
    """Raised when required JSON artifact attachments are missing."""


class DraftSubstitutionError(GmailError):
    """Raised when draft creation is attempted instead of mandatory send."""


class DuplicateSendError(GmailError):
    """Raised when attempting to resend an already-reported series result."""


@runtime_checkable
class IdempotencyStore(Protocol):
    """Protocol for recording sent game report IDs to guarantee idempotency across process restarts."""

    def mark_sent(self, game_uid: str) -> None:
        """Mark a game_uid as sent."""
        ...

    def is_sent(self, game_uid: str) -> bool:
        """Check if a game_uid has already been marked as sent."""
        ...


class FileIdempotencyStore:
    """Durable JSON file-backed idempotency store."""

    def __init__(self, file_path: str | Path = ".sent_game_uids.json") -> None:
        self.file_path = Path(file_path)

    def _load(self) -> set[str]:
        if not self.file_path.exists():
            return set()
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                return set()
        except Exception:
            return set()

    def is_sent(self, game_uid: str) -> bool:
        return game_uid in self._load()

    def mark_sent(self, game_uid: str) -> None:
        sent = self._load()
        sent.add(game_uid)
        if self.file_path.parent:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(sorted(sent), f, indent=2)
        tmp_file.replace(self.file_path)


def validate_oauth_scope(scopes: list[str] | str | None) -> None:
    if scopes is None:
        raise InvalidScopeError("OAuth scope is mandatory and cannot be None.")
    scope_list = [scopes] if isinstance(scopes, str) else list(scopes)
    if not scope_list:
        raise InvalidScopeError("OAuth scope list cannot be empty.")
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
        result: dict[str, Any],
        filename: str | None = None,
        recipient: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """Send one kit-shaped result as the canonical body plus the same file attached.

        The kit's settled convention (SPEC \u00a76.1, WARNINGS \u00a76) is one email per team
        per counted series: the result JSON as the exact canonical bytes in the body, and the
        same file as the single named attachment. The other three artifact kinds are published
        in the repos, never mailed. This is additive: ``send_report`` (the older 14-attachment
        internal-1 path) is untouched.
        """
        if self.idempotency_store.is_sent(game_uid):
            raise DuplicateSendError(f"Report for game_uid '{game_uid}' has already been transmitted.")

        if self._client is None:
            raise GmailClientNotConfiguredError("Gmail service client is not configured.")

        target_recipient = recipient or self.default_recipient
        if not target_recipient:
            raise ValueError("Recipient email address must be explicitly provided or configured.")

        target_subject = subject or f"[PoliceThief-Report] Series {game_uid}"
        # The body must be the exact canonical compact bytes that were hashed -- never a
        # pretty-printed re-serialization (SPEC \u00a76). ``canonical_bytes`` is the compact form.
        body_bytes = canonical_bytes(result)
        body = body_bytes.decode("utf-8")
        game_id_value = result.get("game_id")
        target_filename = filename or result_name(game_id_value if isinstance(game_id_value, str) else "")

        _, raw_b64 = build_email_message(
            sender=self.sender_email,
            recipient=target_recipient,
            subject=target_subject,
            body=body,
            attachments=[(target_filename, body_bytes)],
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
