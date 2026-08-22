from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay import cross_check_uid, verify_dir, verify_log
from common.transport.replay_records import flat_steps_to_kit_doc

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14, "setting": "New York",
          "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
          "thief_start": [3, 3], "cop_start": [0, 0]}
_GAME_UID, _GAME_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "A-vs-B"


def _seal(p: dict) -> dict:
    nonce = new_nonce()
    return {**p, "nonce": nonce, "commit": hash_commit(p, nonce)}


def _honest_steps(n: int = 3, sender: str = "thief", intent: str = "evade") -> list[dict]:
    steps = [_seal({"step": 0, "sender": sender, "intent": "declare"})]
    r, c = (3, 3) if sender == "thief" else (0, 0)
    for i in range(1, n + 1):
        if i % 2 == 0:
            c += 1
            move = "MOVE:E"
        else:
            r += 1
            move = "MOVE:S"
        steps.append(_seal({"step": i, "sender": sender, "intent": intent,
                            "state": f"grid=7x7;self=[{r}, {c}];barriers=[]",
                            "move": move, "hint": "hint"}))
    return steps


def _kit_doc(gid: str, uid: str, own: list[dict], opp: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.1", "game_id": gid, "game_uid": uid,
        "links": {"declaration": f"declaration_{gid}.json", "config": f"config_{gid}_g01.json",
                  "log": f"log_{gid}_g01.json", "result": f"result_{gid}.json"},
        "interop": {"label": "INTERNAL/INTEROP", "boundary": "KitInteropAdapter",
                     "authority": "book App. F table 20"},
        "summary": {"sub_game_number": 1, "outcome": "survival",
                     "steps": len(own) - 1, "audit_ok": True},
        **flat_steps_to_kit_doc(own, opp),
        "mutual_agreement": {"our_result_claim": "survival",
                             "opponent_result_claim": "survival", "audits_passed": True},
    }


def _write_bundle(tmp: Path, doc: dict, own: list[dict], opp: list[dict] | None = None) -> Path:
    p = tmp / f"log_{_GAME_ID}_g01.json"
    p.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
    (tmp / f"config_{_GAME_ID}_g01.json").write_text(
        json.dumps({"schema_version": "1.1", "game_id": _GAME_ID,
                     "game_uid": _GAME_UID, "terms": _TERMS}, sort_keys=True), encoding="utf-8")
    return p


def _tamper_phys(recs: list[dict], idx: int, key: str, val: object) -> list[dict]:
    r = recs[idx]
    r["payload"][key] = val
    r["commit"] = hash_commit(r["payload"], r["nonce"])
    return recs


def _tamper_move(lp: Path, idx: int = 2) -> Path:
    d = json.loads(lp.read_text(encoding="utf-8"))
    d["records"][idx]["payload"]["move"] = "MOVE:W"
    lp.write_text(json.dumps(d, sort_keys=True), encoding="utf-8")
    return lp


def _tamper_state(lp: Path, idx: int = 2) -> Path:
    d = json.loads(lp.read_text(encoding="utf-8"))
    d["records"][idx]["payload"]["state"] = d["records"][idx]["payload"]["state"].replace("[4, 4]", "[4, 5]")
    lp.write_text(json.dumps(d, sort_keys=True), encoding="utf-8")
    return lp


def _foreign_record(step: int, pos: list[int]) -> dict:
    nonce = new_nonce()
    payload = {"step": step, "sender": "thief", "position": pos, "move": "MOVE:N"}
    return {"payload": payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


# TC-RP-02: one-byte mutation → TAMPERED
@pytest.mark.parametrize("mutator", [_tamper_move, _tamper_state])
def test_one_byte_mutation_tampered(tmp_path: Path, mutator: callable) -> None:
    own = _honest_steps(3)
    lp = _write_bundle(tmp_path, _kit_doc(_GAME_ID, _GAME_UID, own), own)
    ok, rpt = verify_log(mutator(lp))
    assert not ok
    assert "TAMPERED" in rpt
    assert "2" in rpt


# TC-RP-03: physics-only → ILLEGAL
@pytest.mark.parametrize("mod, mut", [
    ("off_board", lambda d: _tamper_phys(d["records"], 1, "state",
                     d["records"][1]["payload"]["state"].replace("[4, 3]", "[9, 9]"))),
    ("jump_step", lambda d: _tamper_phys(d["records"], 1, "state",
                     "grid=7x7;self=[6, 5];barriers=[]")),
    ("barrier_quota", lambda d: _tamper_phys(d["records"], 1, "state",
                     f"grid=7x7;self=[4, 3];barriers={[ [i,i] for i in range(15)]}")),
    ("step_ceiling", lambda d: _tamper_phys(d["records"], 1, "step", 37)),
])
def test_physics_fails_not_tampered(tmp_path: Path, mod: str, mut: callable) -> None:
    own = _honest_steps(3)
    lp = _write_bundle(tmp_path, _kit_doc(_GAME_ID, _GAME_UID, own), own)
    d = json.loads(lp.read_text(encoding="utf-8"))
    mut(d)
    lp.write_text(json.dumps(d, sort_keys=True), encoding="utf-8")
    ok, rpt = verify_log(lp)
    assert not ok
    assert "ILLEGAL" in rpt
    assert "TAMPERED" not in rpt


# TC-RP-04: two-sided counting
def test_both_halves_verified(tmp_path: Path) -> None:
    own = _honest_steps(3)
    opp = _honest_steps(2, sender="police", intent="chase")
    lp = _write_bundle(tmp_path, _kit_doc(_GAME_ID, _GAME_UID, own, opp), own, opp)
    ok, rpt = verify_log(lp)
    assert ok
    assert "Verified OK" in rpt
    assert "7 records" in rpt
    assert "both sides'" in rpt


# TC-RP-05: mixed-uid rejected
def test_cross_check_uid_mixed(tmp_path: Path) -> None:
    own = _honest_steps(2)
    _write_bundle(tmp_path, _kit_doc(_GAME_ID, _GAME_UID, own), own)
    other = "11111111-2222-3333-4444-555566667777"
    (tmp_path / f"log_{_GAME_ID}_g02.json").write_text(
        json.dumps(_kit_doc(_GAME_ID, other, own), sort_keys=True), encoding="utf-8")
    result = cross_check_uid(tmp_path)
    assert result is not None
    assert other in result
    assert _GAME_UID in result


# TC-RP-08: foreign degradation
def test_foreign_no_false_tamper(tmp_path: Path) -> None:
    for build_steps in [lambda: [_foreign_record(s, [s, s]) for s in range(3)],
                        lambda: [_foreign_record(1, [1, 1])]]:
        fs = build_steps()
        doc = {"schema_version": "1.1", "game_id": _GAME_ID, "game_uid": _GAME_UID,
               "records": fs, "summary": {"sub_game_number": 1, "outcome": "survival",
                                          "steps": len(fs), "audit_ok": True}}
        lp = tmp_path / f"log_{_GAME_ID}_g01.json"
        lp.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
        (tmp_path / f"config_{_GAME_ID}_g01.json").write_text(
            json.dumps({"terms": _TERMS}, sort_keys=True), encoding="utf-8")
        ok, rpt = verify_log(lp)
        assert ok
        assert "Verified OK" in rpt
        assert "degraded coverage" in rpt
        assert "TAMPERED" not in rpt


# TC-RP-10: golden determinism
def test_deterministic_reports(tmp_path: Path) -> None:
    own = _honest_steps(3)
    lp = _write_bundle(tmp_path, _kit_doc(_GAME_ID, _GAME_UID, own), own)
    r1 = verify_log(lp)[1]
    r2 = verify_log(lp)[1]
    assert r1 == r2

    d = json.loads(lp.read_text(encoding="utf-8"))
    d["records"][2]["payload"]["move"] = "MOVE:W"
    lp.write_text(json.dumps(d, sort_keys=True), encoding="utf-8")
    r1 = verify_log(lp)[1]
    r2 = verify_log(lp)[1]
    assert r1 == r2
    assert "TAMPERED" in r1

    own2 = _honest_steps(2)
    d1, d2 = tmp_path / "run1", tmp_path / "run2"
    d1.mkdir()
    d2.mkdir()
    _write_bundle(d1, _kit_doc(_GAME_ID, _GAME_UID, own2), own2)
    _write_bundle(d2, _kit_doc(_GAME_ID, _GAME_UID, own2), own2)
    assert verify_dir(d1)[:3] == verify_dir(d2)[:3]
