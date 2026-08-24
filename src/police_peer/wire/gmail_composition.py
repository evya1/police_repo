"""Production composition for one settled league-kit result email."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common.config import ConfigError
from common.transport.kit_result_validation import (
    KitResultValidationError,
    validate_emailed_result,
)
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.infra.gmail_oauth import build_gmail_service
from police_peer.reporting.gmail import GMAIL_SEND_SCOPE, FileIdempotencyStore, GmailSender
from police_peer.wire.identity_config import LECTURER_REPORT_ADDRESS, EmailSettings


@dataclass(frozen=True, slots=True)
class GmailDeliveryReceipt:
    """Sanitized local outcome; it never contains addresses, MIME, tokens, or provider IDs."""

    delivery_mode: str
    gmail_api_contacted: bool
    message_composed: bool
    gatekeeper_traversed: bool
    delivery_not_verified: bool


class _CaptureMessages:
    def __init__(self) -> None:
        self.raw = ""

    def send(self, *, userId: str, body: dict[str, str]) -> _CaptureMessages:  # noqa: N803
        if userId != "me" or not isinstance(body.get("raw"), str):
            raise ConfigError("invalid local Gmail capture request")
        self.raw = body["raw"]
        return self

    def execute(self) -> dict[str, str]:
        return {"status": "composed-locally"}


class _CaptureService:
    def __init__(self) -> None:
        self.resource = _CaptureMessages()

    def users(self) -> _CaptureService:
        return self

    def messages(self) -> _CaptureMessages:
        return self.resource


class GmailKitReporter:
    """Validate a published result, then compose locally or call the friend sender."""

    def __init__(
        self, *, settings: EmailSettings, recipient: str, sender_email: str,
        artifact_root: Path, gatekeeper: ExternalApiGatekeeper,
        client_file: Path | None = None, token_file: Path | None = None,
        service_client: Any = None,
    ) -> None:
        self.settings = settings
        self.recipient = recipient
        self.sender_email = sender_email
        self.artifact_root = artifact_root
        self.gatekeeper = gatekeeper
        self.client_file = client_file
        self.token_file = token_file
        self.service_client = service_client

    def report(self, result_path: Path) -> GmailDeliveryReceipt:
        """Send/capture the exact validated result file and write a sanitized receipt."""
        document = _validated_result(result_path)
        game_uid = document["game_uid"]
        capture = _CaptureService() if self.settings.mode == "dry-run" else None
        client = capture or self.service_client or self._live_client()
        state_name = "gmail-dry-run.json" if capture else "gmail-sent.json"
        sender = GmailSender(
            self.gatekeeper, scopes=[GMAIL_SEND_SCOPE], sender_email=self.sender_email,
            default_recipient=self.recipient, service_client=client,
            idempotency_store=FileIdempotencyStore(self.artifact_root / "state" / state_name),
        )
        sender.send_kit_result(
            game_uid=game_uid, result=document, filename=result_path.name,
        )
        if capture is not None:
            _write_message(self.artifact_root, game_uid, capture.resource.raw)
        receipt = GmailDeliveryReceipt(
            delivery_mode=self.settings.mode, gmail_api_contacted=capture is None,
            message_composed=True, gatekeeper_traversed=True, delivery_not_verified=True,
        )
        _write_receipt(self.artifact_root, game_uid, receipt)
        return receipt

    def _live_client(self) -> Any:
        if self.client_file is None or self.token_file is None:
            raise ConfigError("Gmail OAuth file configuration is incomplete")
        return build_gmail_service(client_file=self.client_file, token_file=self.token_file)


def compose_gmail_reporter(
    settings: EmailSettings, artifact_root: Path | str, gatekeeper: ExternalApiGatekeeper, *,
    recipient: str | None = None, authorize_send: bool = False,
    environment: Mapping[str, str] | None = None, service_client: Any = None,
) -> GmailKitReporter | None:
    """Validate runtime inputs and return the counted-series Gmail composition."""
    if settings.mode == "off":
        return None
    env = os.environ if environment is None else environment
    target = (recipient if recipient is not None else settings.recipient).strip()
    if not target or "\n" in target or "\r" in target:
        raise ConfigError("a valid Gmail recipient must be supplied at runtime")
    sender = str(env.get("GMAIL_SENDER_EMAIL", "")).strip()
    if settings.mode == "send":
        if not authorize_send:
            raise ConfigError("live Gmail mode requires --authorize-email-send")
        if target == LECTURER_REPORT_ADDRESS:
            raise ConfigError("live Gmail mode requires a non-placeholder recipient")
        if not sender:
            raise ConfigError("GMAIL_SENDER_EMAIL is required for live Gmail mode")
        client_value = str(env.get("GMAIL_OAUTH_CLIENT_FILE", "")).strip()
        token_value = str(env.get("GMAIL_OAUTH_TOKEN_FILE", "")).strip()
        if service_client is None and (not client_value or not token_value):
            raise ConfigError("Gmail OAuth file environment is required for live Gmail mode")
        client_file = Path(client_value) if client_value else None
        token_file = Path(token_value) if token_value else None
        if service_client is None and not (
            client_file.is_file() or token_file.is_file()
        ):
            raise ConfigError("a local Gmail OAuth client or token file must exist")
    else:
        sender = sender or "sender@example.invalid"
        client_file = token_file = None
    return GmailKitReporter(
        settings=settings, recipient=target, sender_email=sender,
        artifact_root=Path(artifact_root), gatekeeper=gatekeeper,
        client_file=client_file, token_file=token_file, service_client=service_client,
    )


def _validated_result(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return validate_emailed_result(document, filename=path.name)
    except KitResultValidationError as exc:
        raise ConfigError(str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise ConfigError("published Gmail result is malformed") from exc


def _outbox(root: Path, game_uid: str) -> Path:
    path = root / "outbox" / game_uid
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_message(root: Path, game_uid: str, raw: str) -> None:
    _outbox(root, game_uid).joinpath("message.eml").write_bytes(base64.urlsafe_b64decode(raw))


def _write_receipt(root: Path, game_uid: str, receipt: GmailDeliveryReceipt) -> None:
    payload = json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n"
    _outbox(root, game_uid).joinpath("receipt.json").write_text(payload, encoding="utf-8")
