"""Unit tests for the pure internal-interop document builders (T046)."""

from __future__ import annotations

import hashlib
import json

import pytest

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.series import SeriesResult, SeriesRow
from police_peer.reporting import replay_documents as docs
from tests.unit.transport.replay_fixtures import GAME_ID, GAME_UID, TERMS, honest_steps


def _own(n: int = 3, sender: str = "thief") -> tuple:
    records, issues = decode_half(honest_steps(n, sender=sender), "own")
    assert not issues
    return tuple(records)


def _evidence(index: int, opponent: tuple = ()) -> SubgameReplayEvidence:
    return SubgameReplayEvidence(
        sub_game_index=index,
        terms_bytes=canonical_bytes(TERMS),
        own_records=_own(3),
        opponent_records=opponent,
        observed_opponent_commitments=((1, "a" * 64), (0, "b" * 64)),
        our_result_claim="capture",
        opponent_result_claim=None,
        row=SeriesRow(index, Role.THIEF, Outcome.CAPTURE, 3, 0, 1, True),
        game_id=GAME_ID,
        game_uid=GAME_UID,
    )


def _result(entries: tuple | None = None) -> SeriesResult:
    entries = entries if entries is not None else tuple(_evidence(i) for i in range(1, 7))
    return SeriesResult(
        game_id=GAME_ID, game_uid=GAME_UID, ledger=[e.row for e in entries],
        settled=True, settled_outcome=Outcome.CAPTURE, replay_evidence=entries,
    )


class TestSharedIdentityAndLabel:
    def test_config_and_log_share_identity_and_internal_label(self) -> None:
        evidence = _evidence(3)
        cfg, log = docs.build_config(evidence), docs.build_log(evidence)
        for doc in (cfg, log):
            assert doc["game_id"] == GAME_ID
            assert doc["game_uid"] == GAME_UID
            assert doc["sub_game_index"] == 3
            assert doc["schema_status"] == "internal_interop"
            assert doc["schema_version"]
            assert doc["artifact_kind"] in ("config", "log")

    def test_no_document_claims_official_schema(self) -> None:
        result = _result()
        for doc in docs.build_all_documents(result).values():
            parsed = json.loads(doc)
            assert parsed["schema_status"] == "internal_interop"
            assert "official" not in json.dumps(parsed).lower()


class TestLogRecordFlattening:
    def test_own_records_flattened_with_nonce_and_commit(self) -> None:
        evidence = _evidence(1)
        log = docs.build_log(evidence)
        assert len(log["records"]) == len(evidence.own_records)
        for raw, sealed in zip(log["records"], evidence.own_records, strict=True):
            assert raw["nonce"] == sealed.nonce
            assert raw["commit"] == sealed.commitment
            assert raw["step"] == sealed.step

    def test_opponent_records_omitted_when_absent_present_when_supplied(self) -> None:
        assert "opponent_records" not in docs.build_log(_evidence(1))
        with_opp = docs.build_log(_evidence(1, opponent=_own(2, sender="police")))
        assert len(with_opp["opponent_records"]) == 3

    def test_opponent_committed_steps_from_observed_commitments(self) -> None:
        log = docs.build_log(_evidence(1))
        assert log["opponent_committed_steps"] == [0, 1]


class TestBundleMembership:
    def test_result_preserves_unknown_token_usage(self) -> None:
        usage = {
            "series_total": {"status": "unknown", "input_tokens": 0, "output_tokens": 0},
            "per_sub_game": {"1": {"status": "unknown", "input_tokens": 0, "output_tokens": 0}},
        }
        files = docs.build_all_documents(_result(), usage)
        result = json.loads(files[f"result_{GAME_ID}.json"])
        assert result["token_usage"] == usage

    def test_exact_fifteen_members_with_expected_names(self) -> None:
        files = docs.build_all_documents(_result())
        assert len(files) == 15
        assert f"declaration_{GAME_ID}.json" in files
        assert f"result_{GAME_ID}.json" in files
        assert f"manifest_{GAME_ID}.json" in files
        for i in range(1, 7):
            assert f"config_{GAME_ID}_g{i:02d}.json" in files
            assert f"log_{GAME_ID}_g{i:02d}.json" in files

    def test_manifest_digests_match_member_bytes(self) -> None:
        files = docs.build_all_documents(_result())
        manifest = json.loads(files[f"manifest_{GAME_ID}.json"])
        assert len(manifest["members"]) == 14
        for entry in manifest["members"]:
            assert entry["sha256"] == hashlib.sha256(files[entry["name"]]).hexdigest()

    def test_serialize_document_is_utf8_stable_and_newline_terminated(self) -> None:
        doc = {"b": 1, "a": 2}
        data = docs.serialize_document(doc)
        assert data == docs.serialize_document({"a": 2, "b": 1})
        assert data.endswith(b"\n")
        assert data.decode("utf-8")


class TestCrossDocumentCompleteness:
    def test_manifest_counts_agree_with_actual_log_records(self) -> None:
        result = _result()
        files = docs.build_all_documents(result)
        manifest = json.loads(files[f"manifest_{GAME_ID}.json"])
        by_index = {c["sub_game_index"]: c for c in manifest["sub_games"]}
        for i in range(1, 7):
            log = json.loads(files[f"log_{GAME_ID}_g{i:02d}.json"])
            assert by_index[i]["own_record_count"] == len(log["records"])
            assert by_index[i]["own_final_step"] == log["records"][-1]["step"]

    def test_check_completeness_flags_a_truncated_final_record(self) -> None:
        result = _result()
        files = docs.build_all_documents(result)
        manifest = json.loads(files[f"manifest_{GAME_ID}.json"])
        log_docs = {}
        for i in range(1, 7):
            log = json.loads(files[f"log_{GAME_ID}_g{i:02d}.json"])
            if i == 1:
                log["records"] = log["records"][:-1]  # still 0..N-2 contiguous
            log_docs[i] = log
        issues = docs.check_completeness(manifest, log_docs)
        assert any("sub_game 1" in issue for issue in issues)

    def test_check_completeness_passes_untampered_bundle(self) -> None:
        result = _result()
        files = docs.build_all_documents(result)
        manifest = json.loads(files[f"manifest_{GAME_ID}.json"])
        log_docs = {i: json.loads(files[f"log_{GAME_ID}_g{i:02d}.json"]) for i in range(1, 7)}
        assert docs.check_completeness(manifest, log_docs) == []


class TestEvidenceValidation:
    @pytest.mark.parametrize(
        "entries",
        [
            tuple(_evidence(i) for i in range(1, 6)),
            tuple(_evidence(i) for i in (1, 2, 3, 4, 5, 5)),
        ],
    )
    def test_wrong_evidence_shape_rejected(self, entries: tuple) -> None:
        with pytest.raises(docs.ReplayDocumentError):
            docs.build_all_documents(_result(entries))

    def test_empty_own_records_rejected(self) -> None:
        entries = tuple(_evidence(i) for i in range(1, 7))
        entries = entries[:-1] + (
            SubgameReplayEvidence(
                sub_game_index=6, terms_bytes=canonical_bytes(TERMS), own_records=(),
                opponent_records=(), observed_opponent_commitments=(),
                our_result_claim="capture", opponent_result_claim=None,
                row=SeriesRow(6, Role.THIEF, Outcome.CAPTURE, 0, 0, 0, True),
                game_id=GAME_ID, game_uid=GAME_UID,
            ),
        )
        with pytest.raises(docs.ReplayDocumentError):
            docs.build_all_documents(_result(entries))
