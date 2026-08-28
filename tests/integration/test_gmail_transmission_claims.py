"""Live transmission claim semantics: races, ambiguous outcomes, fail-closed retries."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.infra.gatekeeper_types import ExternalCallError
from police_peer.reporting.gmail import DuplicateSendError, GmailTransmissionUncertainError
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import EmailSettings
from tests.integration.gmail_transmission_harness import (
    DropResponseOnceService,
    FailOnceService,
    GatekeeperSpy,
    PreSendFailOnceService,
    SlowService,
    published_result,
)

LIVE_ENV = {"GMAIL_SENDER_EMAIL": "sender@example.invalid"}


def test_two_role_processes_share_one_live_transmission_claim(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path)
    service = SlowService()
    token_path = tmp_path / "oauth" / "token.json"
    environment = {
        "GMAIL_SENDER_EMAIL": "sender@example.invalid",
        "GMAIL_OAUTH_CLIENT_FILE": str(tmp_path / "oauth" / "client.json"),
        "GMAIL_OAUTH_TOKEN_FILE": str(token_path),
    }
    reporters = [
        compose_gmail_reporter(
            EmailSettings("recipient@example.invalid", "send"),
            tmp_path / role,
            GatekeeperSpy(),
            authorize_send=True,
            environment=environment,
            service_client=service,
        )
        for role in ("police", "thief")
    ]
    start = threading.Barrier(2)

    def report(reporter):
        start.wait()
        try:
            reporter.report(path)
        except DuplicateSendError:
            return "duplicate"
        return "sent"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(report, reporters))

    assert sorted(outcomes) == ["duplicate", "sent"]
    assert service.resource.calls == 1
    assert token_path.with_name(".police-thief-gmail-sent.json").is_file()


def test_unacknowledged_gmail_response_keeps_the_live_transmission_claim(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path)
    service = FailOnceService()
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "send"),
        tmp_path,
        GatekeeperSpy(),
        authorize_send=True,
        environment=LIVE_ENV,
        service_client=service,
    )
    # The provider was contacted but returned no message id: the outcome is
    # unknown, so the claim must be retained and a retry must not re-send.
    with pytest.raises(GmailTransmissionUncertainError, match="did not acknowledge"):
        reporter.report(path)
    with pytest.raises(DuplicateSendError):
        reporter.report(path)
    assert service.resource.attempts == 1


def test_definite_failure_before_provider_send_permits_retry(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path)
    service = PreSendFailOnceService()
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "send"),
        tmp_path,
        ExternalApiGatekeeper(),
        authorize_send=True,
        environment=LIVE_ENV,
        service_client=service,
    )
    # The failure happened while building the client, strictly before any
    # provider request existed, so the claim is safely released for a retry.
    # The real Gatekeeper classifies this non-transient pre-send failure.
    with pytest.raises(ExternalCallError):
        reporter.report(path)
    assert service.resource.body is None
    assert reporter.report(path).gmail_api_accepted is True
    assert service.resource.calls == 1


def test_ambiguous_failure_after_transmission_starts_stays_fail_closed(tmp_path: Path) -> None:
    path, _ = published_result(tmp_path)
    service = DropResponseOnceService()
    # A real Gatekeeper proves the uncertain error is a hard failure: even a
    # transient-looking provider exception must never trigger an auto-retry of
    # the non-idempotent users.messages.send operation.
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "send"),
        tmp_path,
        ExternalApiGatekeeper(),
        authorize_send=True,
        environment=LIVE_ENV,
        service_client=service,
    )
    with pytest.raises(GmailTransmissionUncertainError, match="outcome is unknown"):
        reporter.report(path)
    with pytest.raises(DuplicateSendError):
        reporter.report(path)
    assert service.resource.attempts == 1
