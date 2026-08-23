"""The series-wide first-opponent pin (T054).

A six-sub-game series plays exactly ONE opponent. Sub-game 1's opponent is verified by
`PeerFacade._exchange_greeting`; sub-games 2-6 are verified by the per-sub-game negotiation
driver. Before T054 each path kept its own pin, so the driver's started empty and the first
group *it* saw -- sub-game 2's -- became the pin instead of being checked against sub-game
1's. These tests drive the public composition root, not the driver in isolation, because
the defect lived precisely in how the two were wired together.
"""

from __future__ import annotations

import threading

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.refusals import Refused
from police_peer.sdk import create_peer
from tests.unit.wire.test_composition_root import _SAMPLE_CONFIG

# --- first-opponent pin: established at sub-game 1, enforced from sub-game 2 (T054) ----


def test_opponent_swapped_at_subgame_two_is_refused_against_the_subgame_one_pin() -> None:
    """The series pins ONE opponent, and `PeerFacade._exchange_greeting` is where that
    opponent is first verified. Before T054 the per-sub-game driver kept its *own* empty
    pin, so sub-game 1's opponent was never carried forward: the first group the driver
    itself saw was sub-game 2's, and a swap there was silently adopted as the pin rather
    than refused against it.

    `group_id` is not covered by the terms signature, so rewriting it in flight is a real
    impostor an honest peer must reject -- not a synthetic mutation.

    The refusal is attributed to **A** specifically. Letting the swap through also makes
    *B* refuse later (A starts declaring a uid derived from the impostor), and counting
    that downstream refusal as success would score this defect as already fixed.
    """
    ch_a, ch_b = pair("teamA-pin", "teamB-pin")
    original_send_agreement = ch_b.send_agreement

    def impersonating_send_agreement(message: dict):
        # From sub-game 2 onward B claims to be a DIFFERENT group than the one A
        # verified and pinned during the sub-game-1 greeting.
        if int(message.get("sub_game_number", 1)) >= 2:
            message = dict(message)
            message["group_id"] = "teamC-impostor"
            message["identity"] = dict(message.get("identity") or {},
                                       group_id="teamC-impostor")
            message.pop("game_uid", None)  # keep step 7 silent; only the pin may refuse
        return original_send_agreement(message)

    ch_b.send_agreement = impersonating_send_agreement  # type: ignore[method-assign]

    peer_a = create_peer(_SAMPLE_CONFIG, channel=ch_a, role=Role.POLICE, group_id="teamA-pin")
    peer_b = create_peer(_SAMPLE_CONFIG, channel=ch_b, role=Role.THIEF, group_id="teamB-pin")
    caught: dict[str, BaseException] = {}

    def go(key, peer):
        try:
            peer.run()
        except BaseException as exc:  # noqa: BLE001
            caught[key] = exc

    threads = [threading.Thread(target=go, args=kp) for kp in (("a", peer_a), ("b", peer_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    error_a = caught.get("a")
    assert isinstance(error_a, Refused) and error_a.code == "SPAR-N10", (
        "A accepted a changed opponent group at sub-game 2 instead of refusing it "
        f"against its own sub-game-1 pin; A raised {error_a!r}"
    )
    assert "teamC-impostor" in str(error_a) and "opponent changed mid-series" in str(error_a)
