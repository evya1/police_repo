"""Pure builders for internal-interop replay documents (RP-03, RP-08, RP-12).

No filesystem, clock, or network: every function takes immutable evidence and returns a
plain dict or bytes; ``replay_bundle.py`` owns all I/O. Every document is labelled
``schema_status: internal_interop`` (INPUT-001 is unresolved). ``check_completeness``
re-checks a *reloaded* log against the manifest's expected counts (RP-12).
"""

from __future__ import annotations

import hashlib
import json

from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_types import SealedRecord
from common.transport.series import SeriesResult

SCHEMA_VERSION = "internal-interop-1"
SCHEMA_STATUS = "internal_interop"
SUB_GAME_COUNT = 6


class ReplayDocumentError(Exception):
    """Raised when evidence cannot produce a well-formed internal-interop bundle."""


def _base(kind: str, game_id: str, game_uid: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": kind,
        "schema_status": SCHEMA_STATUS,
        "game_id": game_id,
        "game_uid": game_uid,
    }


def _validate_evidence(entries: tuple[SubgameReplayEvidence, ...]) -> None:
    if len(entries) != SUB_GAME_COUNT:
        raise ReplayDocumentError(f"expected {SUB_GAME_COUNT} evidence entries, got {len(entries)}")
    indices = sorted(e.sub_game_index for e in entries)
    if indices != list(range(1, SUB_GAME_COUNT + 1)):
        raise ReplayDocumentError(f"sub_game_index set must be 1..{SUB_GAME_COUNT}, got {indices}")
    for entry in entries:
        if not entry.game_id or not entry.game_uid:
            raise ReplayDocumentError(f"sub-game {entry.sub_game_index} missing game_id/game_uid")
        if not entry.own_records:
            raise ReplayDocumentError(f"sub-game {entry.sub_game_index} has no own records")


def _flatten_record(record: SealedRecord) -> dict:
    payload = json.loads(record.payload_bytes)
    return {**payload, "nonce": record.nonce, "commit": record.commitment}


def _half_counts(records: tuple[SealedRecord, ...]) -> dict:
    if not records:
        return {"record_count": None, "final_step": None}
    return {"record_count": len(records), "final_step": records[-1].step}


def _sub_game_summary(evidence: SubgameReplayEvidence) -> dict:
    own = _half_counts(evidence.own_records)
    opp = _half_counts(evidence.opponent_records)
    return {
        "sub_game_index": evidence.sub_game_index,
        "own_record_count": own["record_count"],
        "own_final_step": own["final_step"],
        "opponent_record_count": opp["record_count"],
        "opponent_final_step": opp["final_step"],
    }


def build_declaration(result: SeriesResult) -> dict:
    # One per series: identity, sub-game count, and final settlement.
    doc = _base("declaration", result.game_id, result.game_uid)
    doc["sub_game_count"] = len(result.ledger)
    doc["settled"] = result.settled
    doc["settled_outcome"] = result.settled_outcome.value if result.settled_outcome else None
    return doc


def build_config(evidence: SubgameReplayEvidence) -> dict:
    # One per sub-game: the agreed terms this sub-game's log is checked against.
    doc = _base("config", evidence.game_id, evidence.game_uid)
    doc["sub_game_index"] = evidence.sub_game_index
    doc["terms"] = json.loads(evidence.terms_bytes)
    return doc


def build_log(evidence: SubgameReplayEvidence) -> dict:
    # One per sub-game, in the field names verify_replay already consumes.
    doc = _base("log", evidence.game_id, evidence.game_uid)
    doc["sub_game_index"] = evidence.sub_game_index
    doc["records"] = [_flatten_record(r) for r in evidence.own_records]
    doc["opponent_committed_steps"] = sorted(s for s, _ in evidence.observed_opponent_commitments)
    if evidence.opponent_records:
        doc["opponent_records"] = [_flatten_record(r) for r in evidence.opponent_records]
    return doc


def build_result(result: SeriesResult) -> dict:
    # One per series: ledger plus the per-sub-game record-count summary (RP-12).
    _validate_evidence(result.replay_evidence)
    doc = _base("result", result.game_id, result.game_uid)
    doc["settled"] = result.settled
    doc["settled_outcome"] = result.settled_outcome.value if result.settled_outcome else None
    doc["ledger"] = [
        {
            "sub_game_number": row.sub_game_number,
            "role": row.role.value,
            "outcome": row.outcome.value,
            "steps": row.steps,
            "score_police": row.score_police,
            "score_thief": row.score_thief,
            "audit_ok": row.audit_ok,
        }
        for row in result.ledger
    ]
    ordered = sorted(result.replay_evidence, key=lambda e: e.sub_game_index)
    doc["sub_games"] = [_sub_game_summary(e) for e in ordered]
    return doc


def build_manifest(result: SeriesResult, members: list[tuple[str, bytes]]) -> dict:
    # The internal transaction/completeness envelope: member digests plus RP-12 counts.
    _validate_evidence(result.replay_evidence)
    doc = _base("manifest", result.game_id, result.game_uid)
    doc["members"] = [
        {"name": name, "sha256": hashlib.sha256(data).hexdigest()} for name, data in members
    ]
    ordered = sorted(result.replay_evidence, key=lambda e: e.sub_game_index)
    doc["sub_games"] = [_sub_game_summary(e) for e in ordered]
    return doc


def serialize_document(doc: dict) -> bytes:
    # UTF-8, stable key ordering, trailing newline.
    return (json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def member_filename(kind: str, game_id: str, sub_game_index: int | None = None) -> str:
    # Deterministic internal filename; declaration/result/manifest are per-series.
    if sub_game_index is None:
        return f"{kind}_{game_id}.json"
    return f"{kind}_{game_id}_g{sub_game_index:02d}.json"


def build_all_documents(result: SeriesResult) -> dict[str, bytes]:
    """Build the exact 15-member set: name -> serialized bytes, manifest included last."""
    _validate_evidence(result.replay_evidence)
    game_id = result.game_id
    entries = sorted(result.replay_evidence, key=lambda e: e.sub_game_index)
    members: list[tuple[str, bytes]] = [
        (member_filename("declaration", game_id), serialize_document(build_declaration(result)))
    ]
    members += [
        (member_filename("config", game_id, e.sub_game_index), serialize_document(build_config(e)))
        for e in entries
    ]
    members += [
        (member_filename("log", game_id, e.sub_game_index), serialize_document(build_log(e)))
        for e in entries
    ]
    members.append((member_filename("result", game_id), serialize_document(build_result(result))))
    manifest_bytes = serialize_document(build_manifest(result, members))
    files = dict(members)
    files[member_filename("manifest", game_id)] = manifest_bytes
    return files


def check_completeness(manifest_doc: dict, log_docs: dict[int, dict]) -> list[str]:
    """RP-12: a reloaded log's actual record count/final step must match the manifest's."""
    expected = {c["sub_game_index"]: c for c in manifest_doc.get("sub_games", [])}
    issues: list[str] = []
    for index, log_doc in log_docs.items():
        exp = expected.get(index)
        if exp is None:
            issues.append(f"sub_game {index}: no manifest entry")
            continue
        own = log_doc.get("records") or []
        if len(own) != exp["own_record_count"] or (own and own[-1]["step"] != exp["own_final_step"]):
            issues.append(f"sub_game {index}: own record count/final step mismatch")
        opp = log_doc.get("opponent_records")
        if exp["opponent_record_count"] is not None:
            mismatch = not opp or len(opp) != exp["opponent_record_count"]
            mismatch = mismatch or (opp and opp[-1]["step"] != exp["opponent_final_step"])
            if mismatch:
                issues.append(f"sub_game {index}: opponent record count/final step mismatch")
        elif opp:
            issues.append(f"sub_game {index}: unexpected opponent records present")
    return issues
