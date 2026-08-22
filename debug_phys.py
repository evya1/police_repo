import json
from pathlib import Path
import tempfile
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay_records import from_kit_record, is_foreign_record, to_kit_record
from common.transport.replay import verify_log, _verify_half
from common.transport.audit import audit_records

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14, "setting": "New York",
          "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
          "thief_start": [3, 3], "cop_start": [0, 0]}

def _seal(payload):
    nonce = new_nonce()
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}

def _honest_steps(n=3):
    steps = [_seal({"step": 0, "sender": "thief", "intent": "declare"})]
    for i in range(1, n + 1):
        steps.append(_seal({
            "step": i, "sender": "thief", "intent": "evade",
            "state": f"grid=7x7;self=[{i}, {i}];barriers=[]",
            "move": "MOVE:N" if i % 2 else "MOVE:E", "hint": "hint",
        }))
    return steps

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    own_steps_flat = _honest_steps(3)
    own_steps = [to_kit_record(s) for s in own_steps_flat]

    print("=== off_board test ===")
    for i, s in enumerate(own_steps):
        print(f"step {i}: is_foreign={is_foreign_record(s['payload'])}")

    # Modify state to [9, 9]
    own_steps[1]["payload"]["state"] = "grid=7x7;self=[9, 9];barriers=[]"
    own_steps[1]["commit"] = hash_commit(own_steps[1]["payload"], own_steps[1]["nonce"])

    for i, s in enumerate(own_steps):
        print(f"step {i} after mod: is_foreign={is_foreign_record(s['payload'])}")

    result = _verify_half(own_steps, _TERMS)
    print(f"_verify_half: passed={result.passed}, detail={result.detail}")
    print(f"failed_steps={result.failed_steps}, tampered_steps={result.tampered_steps}")

    flat_records = [from_kit_record(r) for r in own_steps]
    result2 = audit_records(flat_records, played={}, terms=_TERMS)
    print(f"audit_records: passed={result2.passed}, detail={result2.detail}")
    print(f"failed_steps={result2.failed_steps}, tampered_steps={result2.tampered_steps}")

    print("\n=== step_ceiling test ===")
    own_steps2 = [to_kit_record(s) for s in _honest_steps(3)]
    own_steps2[1]["payload"]["step"] = 37
    own_steps2[1]["commit"] = hash_commit(own_steps2[1]["payload"], own_steps2[1]["nonce"])

    for i, s in enumerate(own_steps2):
        print(f"step {i}: is_foreign={is_foreign_record(s['payload'])}")

    result3 = _verify_half(own_steps2, _TERMS)
    print(f"_verify_half: passed={result3.passed}, detail={result3.detail}")
    print(f"failed_steps={result3.failed_steps}, tampered_steps={result3.tampered_steps}")
