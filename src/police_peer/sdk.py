"""Public SDK facade for the police peer package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.config import ConfigError, load_config
from common.domain.scoring import Role
from common.transport.audit_wire import resolve_audit_wire
from common.transport.loopback import pair
from common.transport.opponent_pin import OpponentPin
from common.transport.series import PeerConfig, PeerFacade, SeriesResult
from police_peer.replay_service import BundleReplayReport
from police_peer.replay_service import verify_bundle as _verify_replay_bundle
from police_peer.strategy import Strategy
from police_peer.wire import BrainDrivenEngine, StandInEngine
from police_peer.wire.config import (
    Budgets,
    PrivateConfig,
    build_budgets,
    load_private,
    peer_locks,
    project_terms,
)
from police_peer.wire.negotiate_per_subgame import negotiated_subgame_driver
from police_peer.wire.startup import SUPPORTED_SCHEMA_VERSIONS, validate_startup_config
from police_peer.wire.strategy_settings import assemble_strategy_config

__version__ = "1.0.0"
__all__ = [
    "Budgets",
    "BundleReplayReport",
    "PeerFacade",
    "SUPPORTED_SCHEMA_VERSIONS",
    "SeriesResult",
    "create_peer",
    "validate_startup_config",
    "verify_replay_bundle",
    "__version__",
]


def verify_replay_bundle(path: str | Path) -> BundleReplayReport:
    """Load and verify one published replay bundle (T047). The sole application entrypoint
    for replay verification — CLI/GUI adapters call only this, never the service module.
    """
    return _verify_replay_bundle(path)


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
    mode: str = "warmup",
    wire_profile: str | None = None,
) -> PeerFacade:
    """Public factory creating a validated PeerFacade.

    Raw shared (JSON) and private (TOML) config are validated/normalized
    ONCE, here, at startup: ``validate_startup_config`` on the shared side,
    ``load_private`` + ``assemble_strategy_config`` on the private side. The
    fully resolved configuration is then passed explicitly to the engine —
    no strategy module reads a file or reaches for global state itself.

    Default behaviour (no explicit ``strategy=``): POLICE sub-games run the
    real, configured ``PoliceBrain`` behind ``BrainDrivenEngine`` (never the
    stand-in — the previous wiring built ``StandInEngine`` unconditionally
    even for POLICE, which made the real brain dead code in production).
    Opposite-role sub-games keep the documented baseline (stand-in)
    behaviour on the same engine (SD-P7).

    An explicitly supplied ``strategy=`` remains backward compatible: it
    selects the legacy ``StandInEngine`` path with that ``Strategy``
    plugged in, for callers that still want to override move selection
    directly rather than through the private ``[strategy]`` config.

    ``wire_profile`` selects the audit wire (T054): the default internal lane
    publishes exactly the T046/T047 bytes, while ``"reference-v3"`` speaks the
    pinned kit's nested audit envelope. It is resolved here, once, and an
    unknown profile fails fast before a game exists.
    """
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

    resolved_seed = seed or private.seed
    peer_budgets = budgets or build_budgets(private)

    peer_cfg = PeerConfig(
        natural_role=role,
        budgets=peer_budgets,
        terms=terms,
        seed=resolved_seed,
        locks=peer_locks(private),
        mode=mode,
    )

    if strategy is not None:
        engine: Any = StandInEngine(
            natural_role=role,
            board_size=int(terms.get("board_size", 7)),
            seed=peer_cfg.seed,
            strategy=strategy,
            terms=terms,
        )
    else:
        strategy_config = assemble_strategy_config(private, raw_config, seed=resolved_seed)
        engine = BrainDrivenEngine(
            natural_role=role,
            board_size=int(terms.get("board_size", 7)),
            seed=peer_cfg.seed,
            terms=terms,
            config=strategy_config,
        )

    if channel is None:
        ch_local, _ = pair(group_id, "loopback-peer")
        channel = ch_local

    # ONE pin and ONE audit wire per series, resolved here and shared by both
    # greeting paths -- never rebuilt inside the driver (T054).
    audit_wire = resolve_audit_wire(wire_profile)
    opponent_pin = OpponentPin()

    return PeerFacade(
        channel=channel,
        engine=engine,
        config=peer_cfg,
        name=group_id,
        mode=mode,
        opponent_pin=opponent_pin,
        subgame_driver=negotiated_subgame_driver(
            group_id, opponent_pin=opponent_pin, audit_wire=audit_wire,
        ),
    )
