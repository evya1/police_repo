"""Integration: two concurrent publishers race for the same UID (T046, ADR-009).

Both publishers build/stage/self-verify independently, then are synchronized with a
barrier right before the O_EXCL lock attempt, so the actual race happens at the lock —
the one operation that decides the outcome. Exactly one must win; the loser must fail
closed with a typed error and leave the winner's bundle untouched.
"""

from __future__ import annotations

import threading
from pathlib import Path

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.series import SeriesResult, SeriesRow
from police_peer.reporting import replay_bundle as bundle
from tests.unit.transport.replay_fixtures import GAME_ID, GAME_UID, TERMS, honest_steps


def _own(n: int = 3) -> tuple:
    records, issues = decode_half(honest_steps(n), "own")
    assert not issues
    return tuple(records)


def _entry(index: int) -> SubgameReplayEvidence:
    return SubgameReplayEvidence(
        sub_game_index=index, terms_bytes=canonical_bytes(TERMS), own_records=_own(3),
        opponent_records=(), observed_opponent_commitments=(), our_result_claim="capture",
        opponent_result_claim=None, row=SeriesRow(index, Role.THIEF, Outcome.CAPTURE, 3, 0, 1, True),
        game_id=GAME_ID, game_uid=GAME_UID,
    )


def _result() -> SeriesResult:
    entries = tuple(_entry(i) for i in range(1, 7))
    return SeriesResult(
        game_id=GAME_ID, game_uid=GAME_UID, ledger=[e.row for e in entries],
        settled=True, settled_outcome=Outcome.CAPTURE, replay_evidence=entries,
    )


def test_two_concurrent_publishers_exactly_one_wins(tmp_path: Path) -> None:
    barrier = threading.Barrier(2)
    outcomes: dict[str, object] = {}

    def synced_hook(checkpoint: str) -> None:
        if checkpoint == "after_self_verify":
            barrier.wait(timeout=5)

    def run(name: str) -> None:
        try:
            outcomes[name] = bundle.publish_replay_bundle(
                tmp_path, _result(), on_checkpoint=synced_hook
            )
        except bundle.ReplayBundleError as exc:
            outcomes[name] = exc

    threads = [threading.Thread(target=run, args=(n,)) for n in ("t1", "t2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
        assert not t.is_alive()

    winners = [v for v in outcomes.values() if isinstance(v, Path)]
    losers = [v for v in outcomes.values() if isinstance(v, bundle.ReplayBundleError)]
    assert len(winners) == 1
    assert len(losers) == 1
    # The loser fails closed either at the lock (typical) or, if the winner's own
    # rename+cleanup completed before the loser's lock attempt ran, at the
    # post-lock existence check — both are typed, both leave the bundle untouched.
    assert isinstance(losers[0], (bundle.PublicationLockError, bundle.ReplayBundleExistsError))

    dest = tmp_path / "replay" / GAME_UID
    assert dest.is_dir()
    assert dest == winners[0]
    assert len(list(dest.iterdir())) == 15

    replay_root = tmp_path / "replay"
    assert not any(p.name.startswith(f".{GAME_UID}.staging-") for p in replay_root.iterdir())
    assert not (replay_root / f".{GAME_UID}.publish.lock").exists()
