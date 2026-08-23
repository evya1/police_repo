"""Shared production-path drivers for the T054 kit-audit tests.

Every helper here drives the *public composition root* (`create_peer` -> `PeerFacade.run`)
over a real loopback pair. Nothing constructs an adapter helper directly: a helper that
passes in isolation while the runtime never calls it is exactly the class of defect these
tests exist to catch.
"""

from __future__ import annotations

import json
import threading

from common.domain.scoring import Role
from common.transport.loopback import pair
from police_peer.sdk import create_peer
from tests.unit.wire.test_composition_root import _SAMPLE_CONFIG

KIT_PROFILE = "reference-v3"


def run_pair(group_a: str = "A", group_b: str = "B", *, wire_profile: str | None = None):
    """Run one full six-sub-game series through the public composition root only."""
    ch_a, ch_b = pair(group_a, group_b)
    return run_pair_on(ch_a, ch_b, group_a, group_b, wire_profile=wire_profile)


def run_pair_on(ch_a, ch_b, group_a: str, group_b: str, *, wire_profile: str | None = None):
    """Same, on channels the caller already built (so it can spy on them first)."""
    kwargs = {} if wire_profile is None else {"wire_profile": wire_profile}
    peer_a = create_peer(_SAMPLE_CONFIG, channel=ch_a, role=Role.POLICE, group_id=group_a, **kwargs)
    peer_b = create_peer(_SAMPLE_CONFIG, channel=ch_b, role=Role.THIEF, group_id=group_b, **kwargs)
    results: dict[str, object] = {}
    errors: list[Exception] = []

    def go(key, peer):
        try:
            results[key] = peer.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=go, args=kp) for kp in (("a", peer_a), ("b", peer_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, f"series errors: {errors}"
    return results.get("a"), results.get("b")


def spy_audits(channel) -> list[dict]:
    """Record every audit payload production hands to this channel's `send_audit`."""
    sent: list[dict] = []
    original = channel.send_audit

    def spy(payload: dict):
        sent.append(payload)
        return original(payload)

    channel.send_audit = spy  # type: ignore[method-assign]
    return sent


def sealed_payloads(result) -> list[dict]:
    """Every sealed own-payload production actually hashed, across all six sub-games."""
    out: list[dict] = []
    for evidence in result.replay_evidence:
        for record in evidence.own_records:
            out.append(json.loads(record.payload_bytes.decode("utf-8")))
    return out
