"""The `PeerChannel` protocol — the seam between transport and series logic.

Every transport implementation (loopback, FastMCP over localhost, etc.) must
implement this protocol. The series engine calls the four `send_*` methods to
push messages outward and the four `poll_*` methods to drain what arrives.

The asymmetry between `send_audit(payload)` and `send_agreement(message)` is
deliberate: it mirrors the reference's tool-name / argument-name contract and
is asserted by TC-01 / TC-02 shape tests.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol


class PeerChannel(Protocol):
    """The surface the series engine uses to reach the opponent."""

    @abstractmethod
    def send_agreement(self, message: dict) -> dict:
        """Push a negotiation greeting / signed terms toward the opponent."""

    @abstractmethod
    def send_turn(self, message: dict) -> dict:
        """Push a turn message toward the opponent."""

    @abstractmethod
    def send_audit(self, payload: dict) -> dict:
        """Push an end-of-game audit reveal toward the opponent."""

    @abstractmethod
    def send_control(self, message: dict) -> dict:
        """Push a control signal (enable / status / restart / quit)."""

    @abstractmethod
    def poll_agreement(self) -> dict | None:
        """Drain one greeting, or return `None` if nothing is waiting."""

    @abstractmethod
    def poll_turn(self) -> dict | None:
        """Drain one turn, or return `None` if nothing is waiting."""

    @abstractmethod
    def poll_audit(self) -> dict | None:
        """Drain one audit, or return `None` if nothing is waiting."""

    @abstractmethod
    def poll_control(self) -> dict | None:
        """Drain one control signal, or return `None` if nothing is waiting."""

    @abstractmethod
    def close(self) -> None:
        """Tear down the channel. No further sends or polls after this."""


# Concrete implementations live in `loopback.py` (in-process) and
# `mcp_client.py` / `mcp_server.py` (HTTP over localhost). Both reimplement
# the same four-send / four-poll surface so the series engine never cares
# which transport is in use.
