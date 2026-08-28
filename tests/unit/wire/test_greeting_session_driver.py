"""Series greeting session regressions at the Police sub-game driver boundary."""

import pytest

from common.domain.scoring import Role
from common.transport.greetings import ConflictingGreetingError
from common.transport.integrity import new_nonce
from common.transport.loopback import pair
from common.transport.negotiate import our_greeting
from common.transport.series import PeerConfig
from police_peer.wire.negotiate_per_subgame import negotiated_subgame_driver
from tests.unit.wire.test_negotiate_per_subgame import (
    _BUDGETS,
    _TERMS,
    _config,
    _negotiate,
    _stub_inner,
)


def test_driver_rejects_a_different_configuration_before_inner_game() -> None:
    ch_a, _ = pair("A", "B")
    calls: list[int] = []
    driver = negotiated_subgame_driver("A", inner=_stub_inner(calls))
    driver(ch_a, None, _config(Role.POLICE), 1)
    changed = PeerConfig(
        natural_role=Role.POLICE, budgets=_BUDGETS,
        terms={**_TERMS, "setting": "Akko"}, locks={},
    )

    with pytest.raises(ConflictingGreetingError, match="different configuration"):
        driver(ch_a, None, changed, 1)
    assert calls == [1]


def test_stale_greeting_is_discarded_before_the_next_subgame() -> None:
    ch_a, ch_b = pair("A", "B")
    driver = negotiated_subgame_driver("A", inner=_stub_inner([]))
    _negotiate(driver, ch_a, ch_b, 2, opp_role=Role.POLICE.value)
    ch_b.send_agreement(our_greeting(
        terms=_TERMS, nonce=new_nonce(), group_id="B", role=Role.POLICE.value,
        sub_game_number=2,
    ))

    sent = _negotiate(driver, ch_a, ch_b, 3, opp_role=Role.THIEF.value)

    assert sent["sub_game_number"] == 3
