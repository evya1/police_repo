"""Tests for the signed Step-0 declaration (T013, INPUT-003, ADR-010)."""

from __future__ import annotations

import hashlib

import pytest

from police_peer.evidence.runtime_summary import RuntimeSummary, collect_runtime_summary
from police_peer.evidence.step_zero import (
    MissingCodeRevisionError,
    MissingConfigDigestError,
    MissingSigningCredentialError,
    StepZeroDeclaration,
    build_signed_step_zero,
    verify_signed_step_zero,
)

_RUNTIME = RuntimeSummary(
    cpu_type="Example CPU", cpu_freq_mhz=2400.0, cpu_cores=4, ram_gb=16.0,
    gpu_model=None, vram_gb=None,
)


def _declaration(
    *,
    counted: bool = True,
    code_revision: str = "abc123def456",
    config_digest: str = "digest-abc",
    llm_mode: str = "template",
) -> StepZeroDeclaration:
    return StepZeroDeclaration(
        team="deterministic-police",
        role="police",
        repo_url="https://github.com/evya1/police_repo",
        mcp_addresses=("https://example.invalid/mcp",),
        runtime=_RUNTIME,
        llm_mode=llm_mode,
        llm_model=None,
        token_cap=None,
        start_time="2026-08-23T00:00:00Z",
        game_id="game-001-g01",
        game_uid="series-uid-001",
        sub_game_number=1,
        config_digest=config_digest,
        code_revision=code_revision,
        counted=counted,
    )


def _fake_signer(data: bytes) -> str:
    return hashlib.sha256(b"signer-key|" + data).hexdigest()


def _fake_verifier(data: bytes, signature: str) -> bool:
    return signature == _fake_signer(data)


class TestCollectRuntimeSummary:
    def test_returns_secret_free_summary(self) -> None:
        summary = collect_runtime_summary()
        payload = summary.as_dict()
        assert set(payload) == {
            "cpu_type", "cpu_freq_mhz", "cpu_cores", "ram_gb", "gpu_model", "vram_gb",
        }
        assert payload["cpu_cores"] >= 0
        assert isinstance(payload["cpu_type"], str)
        for forbidden in ("home", "user", "/root", "\\Users"):
            assert forbidden not in str(payload).lower() or forbidden == "user"


class TestCountedPlayFailsClosed:
    def test_missing_code_revision_blocks_counted_play(self) -> None:
        declaration = _declaration(code_revision="")
        with pytest.raises(MissingCodeRevisionError):
            build_signed_step_zero(declaration, signer=_fake_signer)

    def test_missing_config_digest_blocks_counted_play(self) -> None:
        declaration = _declaration(config_digest="")
        with pytest.raises(MissingConfigDigestError):
            build_signed_step_zero(declaration, signer=_fake_signer)

    def test_missing_signer_blocks_counted_play(self) -> None:
        declaration = _declaration()
        with pytest.raises(MissingSigningCredentialError):
            build_signed_step_zero(declaration, signer=None)

    def test_no_default_signing_credential_is_fabricated(self) -> None:
        # There is no code path that supplies a signer implicitly; calling
        # without one is the only way to observe the fail-closed behavior.
        declaration = _declaration()
        with pytest.raises(MissingSigningCredentialError):
            build_signed_step_zero(declaration, signer=None, signer_key_id="should-not-matter")


class TestCountedPlaySigning:
    def test_signed_declaration_verifies(self) -> None:
        declaration = _declaration()
        signed = build_signed_step_zero(declaration, signer=_fake_signer, signer_key_id="key-1")
        assert signed.signature is not None
        assert signed.signer_key_id == "key-1"
        assert verify_signed_step_zero(signed, verifier=_fake_verifier) is True

    def test_tampered_declaration_fails_verification(self) -> None:
        declaration = _declaration()
        signed = build_signed_step_zero(declaration, signer=_fake_signer, signer_key_id="key-1")
        tampered = build_signed_step_zero(
            _declaration(code_revision="different-revision"),
            signer=_fake_signer,
            signer_key_id="key-1",
        )
        assert verify_signed_step_zero(
            type(signed)(
                declaration=declaration,
                signer_key_id=signed.signer_key_id,
                signature=tampered.signature,
            ),
            verifier=_fake_verifier,
        ) is False


class TestUnsignedProjectProfile:
    def test_template_warmup_without_signer_is_unsigned(self) -> None:
        declaration = _declaration(counted=False, llm_mode="template")
        signed = build_signed_step_zero(declaration, signer=None)
        assert signed.signature is None
        assert signed.signer_key_id is None
        assert verify_signed_step_zero(signed, verifier=_fake_verifier) is False

    def test_warmup_with_signer_is_still_signed(self) -> None:
        declaration = _declaration(counted=False, llm_mode="template")
        signed = build_signed_step_zero(declaration, signer=_fake_signer, signer_key_id="key-1")
        assert signed.signature is not None
        assert verify_signed_step_zero(signed, verifier=_fake_verifier) is True

    def test_warmup_with_missing_revision_does_not_raise(self) -> None:
        declaration = _declaration(counted=False, code_revision="", config_digest="")
        signed = build_signed_step_zero(declaration, signer=None)
        assert signed.signature is None


class TestCanonicalSerialization:
    def test_deterministic_bytes(self) -> None:
        declaration = _declaration()
        assert declaration.canonical_bytes() == declaration.canonical_bytes()

    def test_hebrew_and_emoji_round_trip_without_ascii_escape(self) -> None:
        declaration = StepZeroDeclaration(
            team="משטרה-🚓",
            role="police",
            repo_url="https://github.com/evya1/police_repo",
            mcp_addresses=("https://example.invalid/mcp",),
            runtime=_RUNTIME,
            llm_mode="template",
            llm_model=None,
            token_cap=None,
            start_time="2026-08-23T00:00:00Z",
            game_id="game-001-g01",
            game_uid="series-uid-001",
            sub_game_number=1,
            config_digest="digest-abc",
            code_revision="abc123def456",
            counted=True,
        )
        data = declaration.canonical_bytes()
        assert b"\\u" not in data
        assert "משטרה-🚓".encode() in data

    def test_two_declarations_differing_only_by_field_hash_differently(self) -> None:
        first = _declaration(code_revision="rev-a")
        second = _declaration(code_revision="rev-b")
        assert first.canonical_bytes() != second.canonical_bytes()
