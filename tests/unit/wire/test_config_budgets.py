"""The assembled config must hand PeerConfig budgets it can actually read.

``common.transport.series.Budgets`` is a Protocol read as attributes, so a plain
dict cannot stand in for it. ``assemble_peer_config`` used to return one, which
meant assembling a peer the documented way raised ``AttributeError`` at the first
wait -- invisible because every other test hand-built its own budgets object.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.series import PeerConfig
from police_peer.wire.config import PrivateConfig, assemble_peer_config, build_budgets


def test_assembled_budgets_satisfy_the_series_protocol() -> None:
    assembled = assemble_peer_config("config/game.json", PrivateConfig(), "police")
    config = PeerConfig(
        natural_role=Role.POLICE,
        budgets=assembled["budgets"],
        terms=assembled["terms"],
        seed=assembled["seed"],
        locks=assembled["locks"],
    )
    assert config.budgets.turn_timeout == 30.0
    assert config.budgets.connect_timeout == 30.0
    assert config.budgets.poll_interval == 0.01


def test_private_toml_budgets_reach_the_assembled_config() -> None:
    private = PrivateConfig(budgets={"turn_timeout": 5.0, "poll_interval": 0.25})
    assembled = assemble_peer_config("config/game.json", private, "police")
    assert assembled["budgets"].turn_timeout == 5.0
    assert assembled["budgets"].poll_interval == 0.25
    assert assembled["budgets"].connect_timeout == 30.0


def test_explicit_overrides_win_over_private_toml() -> None:
    private = PrivateConfig(budgets={"turn_timeout": 5.0})
    budgets = build_budgets(private, {"turn_timeout": 9.0})
    assert budgets.turn_timeout == 9.0


def test_create_peer_and_assemble_agree_on_budgets() -> None:
    """One canonical construction: the factory and the assembler must not drift."""
    from police_peer.sdk import create_peer

    private = PrivateConfig(budgets={"turn_timeout": 7.5})
    peer = create_peer("config/game.json", group_id="police-local")
    assembled = assemble_peer_config("config/game.json", PrivateConfig(), "police")
    assert peer.config.budgets.turn_timeout == assembled["budgets"].turn_timeout
    assert build_budgets(private).turn_timeout == 7.5
