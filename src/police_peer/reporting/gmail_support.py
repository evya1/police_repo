"""Small, reusable primitives for the send-only Gmail adapter."""

from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol, runtime_checkable

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailError(Exception):
    """Base error for Gmail reporting operations."""


class GmailClientNotConfiguredError(GmailError):
    """Raised when transmission is attempted without a configured service client."""


class InvalidScopeError(GmailError):
    """Raised when the required send-only OAuth scope is missing or broadened."""


class AttachmentMissingError(GmailError):
    """Raised when required JSON artifact attachments are missing."""


class DraftSubstitutionError(GmailError):
    """Raised when draft creation is attempted instead of mandatory send."""


class DuplicateSendError(GmailError):
    """Raised when attempting to resend an already-reported series result."""


@runtime_checkable
class IdempotencyStore(Protocol):
    """Record sent game report IDs across process restarts."""

    def mark_sent(self, game_uid: str) -> None: ...

    def is_sent(self, game_uid: str) -> bool: ...


class FileIdempotencyStore:
    """Durable JSON file-backed idempotency store."""

    def __init__(self, file_path: str | Path = ".sent_game_uids.json") -> None:
        self.file_path = Path(file_path)

    def _load(self) -> set[str]:
        if not self.file_path.exists():
            return set()
        try:
            with self.file_path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()

    def is_sent(self, game_uid: str) -> bool:
        return game_uid in self._load()

    def mark_sent(self, game_uid: str) -> None:
        sent = self._load()
        sent.add(game_uid)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        temporary.write_text(json.dumps(sorted(sent), indent=2), encoding="utf-8")
        temporary.replace(self.file_path)


def validate_oauth_scope(scopes: list[str] | str | None) -> None:
    if scopes is None:
        raise InvalidScopeError("OAuth scope is mandatory and cannot be None.")
    scope_list = [scopes] if isinstance(scopes, str) else list(scopes)
    if not scope_list:
        raise InvalidScopeError("OAuth scope list cannot be empty.")
    for scope in scope_list:
        normalized = scope.strip()
        if normalized not in (GMAIL_SEND_SCOPE, "gmail.send"):
            raise InvalidScopeError(
                f"Unauthorized OAuth scope '{normalized}'. Only gmail.send is permitted."
            )


def build_email_message(
    *, sender: str, recipient: str, subject: str, body: str,
    attachments: list[tuple[str, bytes]],
) -> tuple[EmailMessage, str]:
    if not attachments:
        raise AttachmentMissingError("Email report must contain at least one JSON attachment.")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = sender, recipient, subject
    message.set_content(body)
    for filename, data in attachments:
        if not data:
            raise AttachmentMissingError(f"Attachment {filename} is empty.")
        message.add_attachment(data, maintype="application", subtype="json", filename=filename)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return message, encoded
