"""Public SDK facade for the police peer package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.config import ConfigError, load_config, validate_config
from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, PeerFacade, SeriesResult
from police_peer.strategy import BaselineStrategy, Strategy
from police_peer.wire import StandInEngine
from police_peer.wire.config import PrivateConfig, load_private, project_terms

__version__ = "1.0.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0", "1.1", "1.2"})

__all__ = [
    "Budgets",
    "PeerFacade",
    "SeriesResult",
    "create_peer",
    "validate_startup_config",
    "__version__",
]


class Budgets:
    """Default turn and connect timeout budgets."""

    def __init__(
        self,
        turn_timeout: float = 30.0,
        connect_timeout: float = 30.0,
        poll_interval: float = 0.01,
    ) -> None:
        self.turn_timeout = turn_timeout
        self.connect_timeout = connect_timeout
        self.poll_interval = poll_interval


def validate_startup_config(raw_config: dict[str, Any]) -> None:
    """Validate raw config at startup, checking schema version and fields."""
    if not isinstance(raw_config, dict):
        raise ConfigError("Config must be a dictionary")
    version = raw_config.get("schema_version")
    if version is None:
        raise ConfigError("Missing required field 'schema_version'")
    if not isinstance(version, str) or version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ConfigError(f"Unsupported schema_version: {version!r}")
    validate_config(raw_config)


def create_peer(
    config_path: str | Path | dict[str, Any],
    *,
    private_config_path: str | Path | None = None,
    channel: Any = None,
    strategy: Strategy | None = None,
    role: Role | str = Role.POLICE,
    seed: int = 0,
    group_id: str = "police-local",
    budgets: Budgets | None = None,
) -> PeerFacade:
    """Public factory creating a validated PeerFacade."""
    if isinstance(config_path, (str, Path)):
        raw_config = load_config(config_path)
    elif isinstance(config_path, dict):
        raw_config = config_path
    else:
        raise ConfigError("config_path must be a file path or dict")

    validate_startup_config(raw_config)

    if isinstance(role, str):
        role = Role(role.lower())

    private = load_private(private_config_path) if private_config_path else PrivateConfig()
    terms = project_terms(raw_config, private.__dict__)
    terms["num_games"] = 6

    movement = raw_config.get("movement_and_barriers", {})
    max_moves = int(movement.get("max_moves", 35))
    survival_thresh = int(movement.get("survival_threshold", 35))
    if max_moves != survival_thresh:
        raise ConfigError(
            f"Operational contract violation (OPEN-011): max_moves ({max_moves}) "
            f"and survival_threshold ({survival_thresh}) must be equal"
        )

    peer_budgets = budgets or Budgets(
        turn_timeout=private.budgets.get("turn_timeout", 30.0),
        connect_timeout=private.budgets.get("connect_timeout", 30.0),
        poll_interval=private.budgets.get("poll_interval", 0.01),
    )

    peer_cfg = PeerConfig(
        natural_role=role,
        budgets=peer_budgets,
        terms=terms,
        seed=seed or private.seed,
    )

    strat = strategy or BaselineStrategy()
    engine = StandInEngine(
        natural_role=role,
        board_size=int(terms.get("board_size", 7)),
        seed=peer_cfg.seed,
        strategy=strat,
    )

    if channel is None:
        ch_local, _ = pair(group_id, "loopback-peer")
        channel = ch_local

    return PeerFacade(channel=channel, engine=engine, config=peer_cfg, name=group_id)
