from __future__ import annotations

import base64
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from common.config import ConfigError
from common.transport.kit_consensus import mutual_agreement
from police_peer.reporting.gmail import DuplicateSendError
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import LECTURER_REPORT_ADDRESS, EmailSettings
from tests.integration.gmail_transmission_harness import (
    GatekeeperSpy,
    Service,
    published_result,
)


def test_dry_run_uses_friend_sender_and_writes_local_outbox(tmp_path: Path) -> None:
    path, document = published_result(tmp_path)
    gatekeeper = GatekeeperSpy()
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), tmp_path, gatekeeper,
    )
    receipt = reporter.report(path)
    outbox = tmp_path / "outbox" / document["game_uid"]
    message = BytesParser(policy=policy.default).parsebytes((outbox / "message.eml").read_bytes())
    (attachment,) = message.iter_attachments()
    assert attachment.get_filename() == path.name
    assert attachment.get_payload(decode=True) == path.read_bytes()
    assert receipt.gmail_api_contacted is False
    assert receipt.gmail_api_accepted is False
    assert gatekeeper.lanes == ["reporting"]
    assert "recipient" not in (outbox / "receipt.json").read_text(encoding="utf-8")


def test_live_mode_reaches_gmail_compatible_client_once(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path)
    gatekeeper, service = GatekeeperSpy(), Service()
    reporter = compose_gmail_reporter(
        EmailSettings("placeholder@example.com", "send"), tmp_path, gatekeeper,
        recipient="recipient@example.invalid", authorize_send=True,
        environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        service_client=service,
    )
    receipt = reporter.report(path)
    message = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(service.resource.body["raw"])
    )
    assert message["To"] == "recipient@example.invalid"
    assert receipt.gmail_api_contacted is True
    assert receipt.gmail_api_accepted is True
    assert gatekeeper.lanes == ["reporting"]
    with pytest.raises(DuplicateSendError):
        reporter.report(path)


def test_explicit_live_mode_accepts_the_official_recipient(tmp_path: Path) -> None:
    gatekeeper, service = GatekeeperSpy(), Service()
    reporter = compose_gmail_reporter(
        EmailSettings(LECTURER_REPORT_ADDRESS, "send"), tmp_path, gatekeeper,
        authorize_send=True, environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        service_client=service,
    )
    assert reporter.recipient == LECTURER_REPORT_ADDRESS


def test_send_requires_authorization_and_confirmed_result(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path, confirmed=False)
    with pytest.raises(ConfigError, match="authorize"):
        compose_gmail_reporter(
            EmailSettings("recipient@example.invalid", "send"), tmp_path, GatekeeperSpy(),
            environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        )
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), tmp_path, GatekeeperSpy(),
    )
    with pytest.raises(ConfigError, match="agreement"):
        reporter.report(path)


def test_send_refuses_missing_local_oauth_files(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="must exist"):
        compose_gmail_reporter(
            EmailSettings("recipient@example.invalid", "send"), tmp_path, GatekeeperSpy(),
            authorize_send=True,
            environment={
                "GMAIL_SENDER_EMAIL": "sender@example.invalid",
                "GMAIL_OAUTH_CLIENT_FILE": str(tmp_path / "missing-client.json"),
                "GMAIL_OAUTH_TOKEN_FILE": str(tmp_path / "missing-token.json"),
            },
        )


def test_rehashed_but_incoherent_result_never_reaches_gmail(tmp_path: Path) -> None:
    path, document = published_result(tmp_path)
    document["sub_games"][0]["score"]["group-a"] = 0
    document["mutual_agreement"] = mutual_agreement(
        document["game_id"], document["final_result"], document["sub_games"], confirmed=True,
    )
    path.write_text(json.dumps(document), encoding="utf-8")
    gatekeeper, service = GatekeeperSpy(), Service()
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "send"), tmp_path, gatekeeper,
        authorize_send=True, environment={"GMAIL_SENDER_EMAIL": "sender@example.invalid"},
        service_client=service,
    )
    with pytest.raises(ConfigError, match="malformed"):
        reporter.report(path)
    assert service.resource.body is None
    assert gatekeeper.lanes == []
