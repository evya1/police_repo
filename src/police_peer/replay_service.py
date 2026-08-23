"""Application service: load, validate, and verify one published replay bundle (T047).

Owns manifest discovery, exact membership/digests, pairing by content identity (never
filename — F-05), the RP-12 count check, and aggregation into one frozen report (ADR-008).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayReport, ReplayVerdict, VerificationCoverage
from police_peer.reporting.replay_documents import SUB_GAME_COUNT, check_completeness

_IDENTITY_KEYS = ("game_id", "game_uid", "sub_game_index")
_RANK = {
    ReplayVerdict.VERIFIED_OK: 0, ReplayVerdict.INCOMPLETE: 1, ReplayVerdict.INVALID: 1,
    ReplayVerdict.ILLEGAL: 2, ReplayVerdict.TAMPERED: 3,
}
_NO_COVERAGE = VerificationCoverage(False, False, False, False, False, False)
_COVERAGE_FIELDS = (
    "integrity", "live_binding", "physics", "outcome", "bundle_digests", "external_authenticity"
)
_AND_LAYERS = ("integrity", "live_binding", "physics", "outcome")
Issue = tuple[ReplayVerdict, str]


class ReplayServiceError(Exception):
    """A path/usage problem: the bundle directory is missing or unreadable."""


def _issue_json(i) -> dict:
    return {"code": i.code, "message": i.message, "step": i.step, "half": i.half}


def _sg_json(sg: SubGameOutcome) -> dict:
    return {
        "sub_game_index": sg.sub_game_index, "verdict": sg.report.verdict.value,
        "issues": [_issue_json(i) for i in sg.report.issues],
    }


@dataclass(frozen=True, slots=True)
class SubGameOutcome:
    """One sub-game's pure verification result, tied to its manifest index."""

    sub_game_index: int
    report: ReplayReport


@dataclass(frozen=True, slots=True)
class BundleReplayReport:
    """Full bundle outcome: verdict, layered coverage, every sub-game, structural issues."""

    game_id: str
    game_uid: str
    verdict: ReplayVerdict
    coverage: VerificationCoverage
    checked_records: int
    sub_games: tuple[SubGameOutcome, ...]
    issues: tuple[str, ...]

    def to_json(self) -> dict:
        return {
            "game_id": self.game_id, "game_uid": self.game_uid, "verdict": self.verdict.value,
            "coverage": {f: getattr(self.coverage, f) for f in _COVERAGE_FIELDS},
            "checked_records": self.checked_records,
            "sub_games": [_sg_json(sg) for sg in self.sub_games],
            "issues": list(self.issues),
        }

    def to_human(self) -> str:
        cov = ", ".join(f"{f}={getattr(self.coverage, f)}" for f in _COVERAGE_FIELDS)
        lines = [f"bundle {self.game_uid} ({self.game_id}): {self.verdict.value.upper()}", f"coverage: {cov}"]
        if not self.coverage.external_authenticity:
            lines.append("NOTE: unanchored bundle — never reported as externally authentic.")
        lines += [f"  sub_game {sg.sub_game_index}: {sg.report.verdict.value}" for sg in self.sub_games]
        lines += [f"  ! {issue}" for issue in self.issues]
        return "\n".join(lines)


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _structural(directory: Path) -> tuple[ReplayVerdict | None, dict | None, list[str]]:
    """Manifest discovery, exact membership, per-file digests. No verify_replay yet."""
    manifests = sorted(directory.glob("manifest_*.json"))
    if len(manifests) != 1:
        return ReplayVerdict.INVALID, None, [f"expected exactly one manifest, found {len(manifests)}"]
    manifest_doc = _load_json(manifests[0])
    if not isinstance(manifest_doc, dict) or manifest_doc.get("game_uid") != directory.name:
        return ReplayVerdict.INVALID, None, ["manifest missing/unreadable or game_uid mismatch"]
    members = manifest_doc.get("members")
    if not isinstance(members, list) or not members:
        return ReplayVerdict.INVALID, manifest_doc, ["manifest has no members"]

    expected = {manifests[0].name} | {m.get("name") for m in members}
    actual = {p.name for p in directory.iterdir() if p.is_file()}
    problems = (
        [(ReplayVerdict.INVALID, f"extra member: {n}") for n in sorted(actual - expected)]
        + [(ReplayVerdict.INCOMPLETE, f"missing member: {n}") for n in sorted(expected - actual)]
        + [
            (ReplayVerdict.TAMPERED, f"digest mismatch: {m['name']}") for m in members
            if m.get("name") in actual and _digest(directory / m["name"]) != m.get("sha256")
        ]
    )
    if not problems:
        return None, manifest_doc, []
    worst = max((v for v, _ in problems), key=lambda v: _RANK[v])
    return worst, manifest_doc, [msg for _, msg in problems]


def _load_kind(directory: Path, glob: str, kind: str) -> list[dict]:
    docs = (_load_json(p) for p in sorted(directory.glob(glob)))
    return [d for d in docs if isinstance(d, dict) and d.get("artifact_kind") == kind]


def _pair_and_verify(directory: Path, manifest: dict) -> tuple[list[Issue], list[SubGameOutcome]]:
    """RP-05/F-05: pair by content identity, never filename (unparseable/mismatched -> INVALID;
    RP-12 manifest-vs-reload count mismatch -> INCOMPLETE, a separate signal)."""
    game_id = manifest["game_id"]
    configs = _load_kind(directory, f"config_{game_id}_g*.json", "config")
    logs = _load_kind(directory, f"log_{game_id}_g*.json", "log")

    issues: list[Issue] = []
    if len(logs) != SUB_GAME_COUNT:
        issues.append((ReplayVerdict.INVALID, f"expected {SUB_GAME_COUNT} parseable logs, found {len(logs)}"))

    log_docs: dict[int, dict] = {}
    outcomes: list[SubGameOutcome] = []
    for log_doc in logs:
        idx = log_doc.get("sub_game_index")
        matches = [c for c in configs if all(c.get(k) == log_doc.get(k) for k in _IDENTITY_KEYS)]
        if len(matches) != 1:
            issues.append(
                (ReplayVerdict.INVALID, f"sub_game {idx}: found {len(matches)} matching configs, need exactly 1")
            )
            continue
        log_docs[idx] = log_doc
        outcomes.append(SubGameOutcome(idx, verify_replay(log_doc, matches[0])))

    issues += [(ReplayVerdict.INCOMPLETE, msg) for msg in check_completeness(manifest, log_docs)]
    return issues, sorted(outcomes, key=lambda o: o.sub_game_index)


def _aggregate(
    game_id: str, game_uid: str, structural_issues: list[Issue], outcomes: list[SubGameOutcome]
) -> BundleReplayReport:
    messages = tuple(msg for _, msg in structural_issues)
    if not outcomes:
        verdict = max((v for v, _ in structural_issues), key=lambda v: _RANK[v], default=ReplayVerdict.INVALID)
        return BundleReplayReport(game_id, game_uid, verdict, _NO_COVERAGE, 0, (), messages)

    candidates = [o.report.verdict for o in outcomes] + [v for v, _ in structural_issues]
    verdict = max(candidates, key=lambda v: _RANK[v])
    layers = {n: all(getattr(o.report.coverage, n) for o in outcomes) for n in _AND_LAYERS}
    coverage = VerificationCoverage(**layers, bundle_digests=True, external_authenticity=False)
    checked = sum(o.report.checked_records for o in outcomes)
    return BundleReplayReport(game_id, game_uid, verdict, coverage, checked, tuple(outcomes), messages)


def verify_bundle(path: Path | str) -> BundleReplayReport:
    """Load exactly one UID directory and verify it end to end: all verification math
    lives in ``verify_replay``, all counting in ``check_completeness`` — this orchestrates.
    """
    directory = Path(path)
    if not directory.is_dir():
        raise ReplayServiceError(f"not a directory: {directory}")

    struct_verdict, manifest_doc, struct_issues = _structural(directory)
    game_id = manifest_doc.get("game_id", "") if isinstance(manifest_doc, dict) else ""
    if struct_verdict is not None:
        return BundleReplayReport(
            game_id, directory.name, struct_verdict, _NO_COVERAGE, 0, (), tuple(struct_issues)
        )

    pairing_issues, outcomes = _pair_and_verify(directory, manifest_doc)
    return _aggregate(game_id, directory.name, pairing_issues, outcomes)
