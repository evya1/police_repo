"""Headless replay verification — the book's Replay Viewer, minus the GUI.

Verdicts are exactly ``Verified OK``, ``TAMPERED``, or ``ILLEGAL`` (FR-RP-08).
"""

from __future__ import annotations

import json
from pathlib import Path

from common.transport.audit import AuditResult, audit_records
from common.transport.canonical import commit as hash_commit
from common.transport.replay_records import from_kit_record, is_foreign_record


def _terms_beside(path: Path) -> dict:
    for cfg in sorted(path.parent.glob("config_*.json")):
        try:
            terms = json.loads(cfg.read_text(encoding="utf-8")).get("terms")
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(terms, dict):
            return terms
    return {}


def _verify_foreign_half(records: list[dict]) -> AuditResult:
    failed, tampered, notes, verified = [], [], [], 0
    for rec in records:
        flat = from_kit_record(rec)
        step = int(flat.get("step", -1))
        commit = flat.get("commit")
        if commit is None:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing commit")
            continue
        payload = {k: v for k, v in flat.items() if k not in ("commit", "nonce")}
        computed = hash_commit(payload, flat.get("nonce", ""))
        if computed != commit:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: committed {commit}, rehash {computed}")
        elif step >= 1:
            verified += 1
    notes.append("degraded coverage: foreign-shaped records verified integrity-only; physics and intent not enforced")
    return AuditResult(passed=len(failed) == 0, verified_steps=verified, failed_steps=failed,
                       tampered_steps=tampered, detail="; ".join(notes[:3]) if notes else "")


def _verify_half(records: list[dict], terms: dict) -> AuditResult:
    if not records:
        return AuditResult(passed=True, verified_steps=0)
    has_foreign = any(int(from_kit_record(r).get("step", 0)) >= 1
                      and is_foreign_record(r.get("payload", {})) for r in records)
    if has_foreign:
        return _verify_foreign_half(records)
    return audit_records([from_kit_record(r) for r in records], played={}, terms=terms)


def verify_log(path: Path) -> tuple[bool, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    records = doc.get("records") or []
    if not records:
        return False, f"{path.name}: no records — the game left nothing to verify"
    terms = _terms_beside(path)
    halves: list[tuple[str, list[dict]]] = [("own", records)]
    if doc.get("opponent_records"):
        halves.append(("opponent", doc["opponent_records"]))
    lines, ok, total, notes = [], True, 0, []
    for label, recs in halves:
        result = _verify_half(recs, terms)
        total += len(recs)
        if result.detail:
            notes.append(f"{path.name} ({label} records): {result.detail}")
        if result.passed:
            continue
        ok = False
        if result.tampered_steps:
            verdict = f"TAMPERED — steps {result.tampered_steps} do not reproduce their commitments"
        else:
            verdict = f"ILLEGAL — every record re-hashes, but steps {result.failed_steps} break the signed physics"
        lines.append(f"{path.name} ({label} records): {verdict}\n    {result.detail}")
    if ok:
        sides = "both sides'" if len(halves) > 1 else "one side's"
        report = f"{path.name}: Verified OK — {total} records re-hashed against their commitments ({sides} sealed half)"
        if notes:
            report += "\n  " + "\n  ".join(notes)
        return True, report
    return False, "\n  ".join(lines)


def verify_dir(root: Path) -> tuple[int, int, list[str]]:
    lines, ok, bad = [], 0, 0
    for p in sorted(root.rglob("log_*.json")):
        good, rpt = verify_log(p)
        lines.append(("  " if good else "  ") + rpt)
        if good:
            ok += 1
        else:
            bad += 1
    return ok, bad, lines


def cross_check_uid(root: Path) -> str | None:
    uids: set[str] = set()
    for p in sorted(root.rglob("*.json")):
        try:
            uid = json.loads(p.read_text(encoding="utf-8")).get("game_uid")
        except (ValueError, UnicodeDecodeError):
            continue
        if uid is not None:
            uids.add(uid)
    if len(uids) > 1:
        return (f"artifacts carry {len(uids)} different game_uids: {sorted(uids)} — "
                "they do not all belong to one match, so verifying them together proves nothing")
    return None
