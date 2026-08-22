from __future__ import annotations

import pytest

from police_peer.reporting.schemas import (
    SignatureError,
    build_declaration,
    build_sub_game_log,
    finalize_log,
    sign_artifact,
    verify_artifact,
)


def test_signing_seam():
    declaration = build_declaration(
        game_uid="test_game",
        team="test_team",
        role="police",
        members=[],
        police_repo_url="http://example.com",
        thief_repo_url="http://example.com",
        mcp_addresses=[],
        hardware="test_hardware",
        model="test_model",
        token_budget=100,
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-02T00:00:00Z",
    )

    # Test that signing fails with None signer
    with pytest.raises(SignatureError):
        sign_artifact(declaration, None)

    # Test signing with a fake signer
    def fake_signer(data):
        from common.transport.canonical import commit
        return commit(declaration.as_dict(), "test_nonce")

    signature = sign_artifact(declaration, fake_signer)
    assert signature is not None

    # Test verification
    def fake_verifier(data, sig):
        from common.transport.canonical import verify_commit
        return verify_commit(declaration.as_dict(), "test_nonce", sig)

    assert verify_artifact(declaration, signature, fake_verifier)

    # Test tampered artifact
    declaration.team = "tampered_team"
    assert not verify_artifact(declaration, signature, fake_verifier)


def test_finalize_log_atomicity_on_signer_failure():
    log = build_sub_game_log(game_uid="g-atom", game_id="g-atom:0")
    assert log.finalized is False
    assert log.signature is None

    def failing_signer(data: bytes) -> str:
        raise RuntimeError("Signer hardware failure")

    with pytest.raises(RuntimeError, match="Signer hardware failure"):
        finalize_log(log, failing_signer)

    # Verify log was atomically rolled back to unfinalized state
    assert log.finalized is False
    assert log.signature is None

    # Verify that a subsequent successful sign works cleanly
    def good_signer(data: bytes) -> str:
        return "valid-sig-123"

    finalize_log(log, good_signer)
    assert log.finalized is True
    assert log.signature == "valid-sig-123"
