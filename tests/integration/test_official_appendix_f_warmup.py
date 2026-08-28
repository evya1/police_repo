"""Credential-free end-to-end proof for the exact Appendix-F projection."""

from __future__ import annotations

import json
from email import policy
from email.parser import BytesParser

from common.transport.kit_bundle_validation import validate_official_bundle
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.sdk import verify_replay_bundle
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import EmailSettings
from tests.integration.test_kit_bundle_emission import bundle as bundle
from tests.integration.test_kit_bundle_emission import docs
from tests.integration.test_kit_bundle_emission import official_args as official_args
from tests.integration.test_kit_bundle_emission import series as series


class _Gatekeeper:
    def execute(self, call, *args, **kwargs):
        return call(*args, **kwargs)


def test_internal_evidence_bundle_remains_separate(series, official_args, tmp_path):
    internal = publish_replay_bundle(tmp_path, series)
    publish_kit_bundle(
        tmp_path, series, our_group="kit-police", counted=False, **official_args,
    )
    assert len(list(internal.iterdir())) == 15
    assert verify_replay_bundle(internal).verdict.value == "verified_ok"


def test_emitted_documents_have_the_exact_reference_keys(bundle):
    every = docs(bundle)
    declaration = next(doc for name, doc in every.items() if name.startswith("declaration_"))
    config = next(doc for name, doc in every.items() if name.startswith("config_"))
    log = next(doc for name, doc in every.items() if name.startswith("log_"))
    result = next(doc for name, doc in every.items() if name.startswith("result_"))

    assert set(declaration) == {
        "_schema", "schema_version", "declaration_type", "game_id", "game_uid", "links",
        "timezone", "game_started_at", "game_ended_at", "num_sub_games",
        "max_tokens_per_game", "groups",
    }
    assert set(config) == {
        "_schema", "schema_version", "_note", "agreed_between", "board_and_agents",
        "movement_and_barriers", "scoring", "pheromones", "network_and_league",
        "rate_limiter_gatekeeper", "game_id", "game_uid", "sub_game_number", "links",
        "config_name", "config_sha256",
    }
    assert set(log) == {
        "_schema", "schema_version", "game_id", "game_uid", "links", "summary", "records",
        "mutual_agreement",
    }
    assert set(result) == {
        "_schema", "schema_version", "report_type", "game_id", "game_uid", "links",
        "timezone", "groups", "num_sub_games", "sub_games", "final_result",
        "mutual_agreement",
    }
    assert len(result["sub_games"]) == 6
    assert all(set(record) == {"payload", "nonce", "commit"} for record in log["records"])


def test_warmup_reopens_validates_and_attaches_the_exact_result(bundle):
    result = validate_official_bundle(bundle)
    for path in bundle.glob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
    result_path = bundle / f"result_{result['game_id']}.json"
    root = bundle.parent.parent
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), root, _Gatekeeper(),
    )

    receipt = reporter.report(result_path)

    message_path = root / "outbox" / result["game_uid"] / "message.eml"
    message = BytesParser(policy=policy.default).parsebytes(message_path.read_bytes())
    (attachment,) = message.iter_attachments()
    assert attachment.get_filename() == result_path.name
    assert attachment.get_payload(decode=True) == result_path.read_bytes()
    assert receipt.gmail_api_contacted is False
    serialized = b"".join(path.read_bytes() for path in bundle.glob("*.json"))
    assert not any(secret in serialized for secret in (
        b"OPENROUTER_API_KEY", b"GMAIL_OAUTH", b"credentials.json", b"token.json",
    ))
