"""Police peer wire adapters — re-exports only.

``StandInEngine`` (baseline) and ``BrainDrivenEngine`` (real PoliceBrain on
POLICE sub-games) both compose ``SubgameSession``; neither subclasses the
other. Both peers import the same shared transport code and parameterize by
role.
"""

from __future__ import annotations

from common.transport.series import TurnEngine as TurnEngine
from police_peer.wire.brain import BrainDrivenEngine
from police_peer.wire.session import SubgameSession
from police_peer.wire.stand_in import StandInEngine

__all__ = ["BrainDrivenEngine", "StandInEngine", "SubgameSession", "TurnEngine"]
