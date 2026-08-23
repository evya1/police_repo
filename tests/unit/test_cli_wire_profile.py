"""The `--wire-profile` flag reaches `create_peer`, so the kit lane is selectable in production.

``KitAuditWire`` (``reference-v3``) existed and was proven in isolation, but the only real
entry point -- ``cli.main`` -> ``runner.run_one_peer`` -> ``sdk.create_peer`` -- never passed
a profile, so every process built the ``internal`` lane no matter who the opponent was.
Against a `copthief-league-protocol` peer that ships a flat audit under an internal top
level: the opponent verifies zero records and settles ``tamper_forfeit``, which App. E
rule 35 zeroes for BOTH teams. An adapter the runtime cannot select is not wired.
"""

from __future__ import annotations

import pytest

from common.transport.audit_wire import KitAuditWire
from police_peer import runner
from police_peer.cli import build_parser, main


def test_wire_profile_defaults_to_none_so_behaviour_is_unchanged() -> None:
    assert build_parser().parse_args([]).wire_profile is None


def test_wire_profile_accepts_the_kit_lane() -> None:
    assert build_parser().parse_args(["--wire-profile", "reference-v3"]).wire_profile == "reference-v3"


def test_unknown_wire_profile_is_refused_at_the_command_line() -> None:
    """A typo must fail loudly here, not silently fall back to the internal lane."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--wire-profile", "reference-v4"])


def test_main_forwards_the_profile_to_the_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        "police_peer.cli.run_one_peer", lambda **kwargs: seen.update(kwargs) or 0
    )
    assert main(["--wire-profile", "reference-v3"]) == 0
    assert seen["wire_profile"] == "reference-v3"


def test_runner_forwards_the_profile_to_create_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seam that was actually missing: runner -> create_peer."""
    seen: dict[str, object] = {}

    monkeypatch.setattr(runner, "serve_background", lambda *a, **k: None)
    monkeypatch.setattr(runner, "edge_answers", lambda *a, **k: True)
    monkeypatch.setattr(runner, "McpChannel", lambda *a, **k: _StubChannel())

    def _fake_create_peer(**kwargs: object) -> object:
        seen.update(kwargs)
        return _StubFacade()

    monkeypatch.setattr(runner, "create_peer", _fake_create_peer)
    runner.run_one_peer(wire_profile="reference-v3")
    assert seen["wire_profile"] == "reference-v3"


def test_the_kit_profile_resolves_to_the_kit_adapter() -> None:
    """End of the chain: the string the CLI accepts builds the nested-envelope adapter."""
    from common.transport.audit_wire import resolve_audit_wire

    assert isinstance(resolve_audit_wire("reference-v3"), KitAuditWire)


class _StubChannel:
    def close(self) -> None:
        return None


class _StubResult:
    settled = True


class _StubFacade:
    def run(self) -> _StubResult:
        return _StubResult()
