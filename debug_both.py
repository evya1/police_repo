import json
from pathlib import Path
import tempfile
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay_records import from_kit_record, is_foreign_record, to_kit_record
from common.transport.replay import verify_log, _verify_half

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14, "setting": "New York",
          "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
          "thief_start": [3, 3], "cop_start": [0, 0]}

def _seal(payload):
    nonce = new_nonce()
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}

def _honest_steps(n=3, sender="thief", intent="evade"):
    steps = [_seal({"step": 0, "sender": sender, "intent": "declare"})]
    for i in range(1, n + 1):
        steps.append(_seal({
            "step": i, "sender": sender, "intent": intent,
            "state": f"grid=7x7;self=[{i}, {i}];barriers=[]",
            "move": "MOVE:N" if i % 2 else "MOVE:E", "hint": "hint",
        }))
    return steps

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    own_steps = [to_kit_record(s) for s in _honest_steps(3)]
    opp_steps = [to_kit_record(s) for s in _honest_steps(2, sender="police", intent="chase")]

    print("=== own steps ===")
    for i, s in enumerate(own_steps):
        flat = from_kit_record(s)
        print(f"step {i}: is_foreign={is_foreign_record(s['payload'])}")

    print("\n=== opp steps ===")
    for i, s in enumerate(opp_steps):
        flat = from_kit_record(s)
        print(f"step {i}: is_foreign={is_foreign_record(s['payload'])}")

    result_own = _verify_half(own_steps, _TERMS)
    print(f"\nown _verify_half: passed={result_own.passed}, detail={result_own.detail}")
    print(f"failed_steps={result_own.failed_steps}, tampered_steps={result_own.tampered_steps}")

    result_opp = _verify_half(opp_steps, _TERMS)
    print(f"\nopp _verify_half: passed={result_opp.passed}, detail={result_opp.detail}")
    print(f"failed_steps={result_opp.failed_steps}, tampered_steps={result_opp.tampered_steps}")

    # Write log
    log_doc = {
        "schema_version": "1.1", "game_id": "A-vs-B", "game_uid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "records": own_steps,
        "opponent_records": opp_steps,
        "summary": {"sub_game_number": 1, "outcome": "survival", "steps": 3, "audit_ok": True},
    }
    log_path = tmp_path / "log_A-vs-B_g01.json"
    log_path.write_text(json.dumps(log_doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "config_A-vs-B_g01.json").write_text(json.dumps({"terms": _TERMS}, sort_keys=True), encoding="utf-8")

    ok, report = verify_log(log_path)
    print(f"\nok={ok}")
    print(f"report={report}")
