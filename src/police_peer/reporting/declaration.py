"""Declaration composition and result-agreement helpers for the runner (T057/T058).

Split out of ``runner.py`` to keep that module under the repository's own line cap; these are
pure(ish) composition helpers with no FastMCP/process wiring of their own.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

from common.config import PrivateConfig as DeclaredPrivateConfig
from common.config import load_private as load_declared_private
from common.transport.kit_agreement import AgreementOutcome, build_proposal
from common.transport.kit_identity import group_block
from common.transport.kit_settlement import result_row, series_final
from common.transport.series import SeriesResult
from police_peer.evidence.identity_source import build_identity
from police_peer.wire.result_agreement import exchange as exchange_result_agreement

#: This project's own code version -- the identity declaration's ``code_version`` field.
CODE_VERSION = "1.00"

logger = logging.getLogger(__name__)


def declared_private(
    private_config: Path | str | None, overrides: dict | None
) -> DeclaredPrivateConfig:
    """Load the declared-identity private config (T057), then apply CLI overrides.

    Distinct from ``police_peer.wire.config.PrivateConfig`` (physics/wire tuning): this is the
    App. B §4 declaration-oriented private config (identity, email, llm policy).
    """
    base = load_declared_private(private_config) if private_config else DeclaredPrivateConfig()
    overrides = overrides or {}
    fields = {f.name: getattr(base, f.name) for f in dataclasses.fields(base)}
    if "group_id" in overrides:
        fields["group_id"] = overrides["group_id"]
    if "members" in overrides:
        fields["members"] = overrides["members"]
    if overrides.get("repos_cop") or overrides.get("repos_thief"):
        repos = dict(fields.get("repos") or {})
        if overrides.get("repos_cop"):
            repos["cop"] = overrides["repos_cop"]
        if overrides.get("repos_thief"):
            repos["thief"] = overrides["repos_thief"]
        fields["repos"] = repos
    if overrides.get("public_url"):
        mcp_servers = dict(fields.get("mcp_servers") or {})
        mcp_servers["cop"] = mcp_servers.get("cop") or overrides["public_url"]
        mcp_servers["thief"] = mcp_servers.get("thief") or overrides["public_url"]
        fields["mcp_servers"] = mcp_servers
    return DeclaredPrivateConfig(**fields)


def our_identity_block(
    declared: DeclaredPrivateConfig, *, group_id: str, counted_games_played: int
) -> dict | None:
    """Best-effort declaration group block for OUR side. Never fabricated: a run whose
    private config is incomplete simply omits its identity block rather than inventing one."""
    try:
        identity = build_identity(
            declared,
            group_id=group_id,
            repo_root=Path.cwd(),
            code_version=CODE_VERSION,
            counted_games_played=counted_games_played,
        )
    except Exception as exc:  # noqa: BLE001 - identity is additive evidence, never fatal here
        logger.info("No group identity available for the declaration: %s", exc)
        return None
    return group_block(identity)


def kit_rows_and_final(result: SeriesResult, *, our_group: str) -> tuple[list[dict], dict]:
    """The same row/aggregate projection kit_bundle.py uses, built once here so both the
    agreement exchange and the published bundle settle on IDENTICAL bytes (CT-08)."""
    theirs = result.opponent_group_id
    rows = [
        result_row(
            row=row, our_group=our_group, opponent_group=theirs,
            tokens={our_group: 0, theirs: 0},
            log_file=f"log_{result.game_id}_g{row.sub_game_number:02d}.json",
        )
        for row in sorted(result.ledger, key=lambda r: r.sub_game_number)
    ]
    final = series_final(rows, (our_group, theirs), counted=False)
    return rows, final


def agree_on_result(
    channel, result: SeriesResult, *, our_group: str, budget: float
) -> AgreementOutcome:
    """Exchange the mutual result-agreement proposal exactly once, over the same channel the
    series just played on (CT-08). Never raises: see wire/result_agreement.exchange."""
    rows, final = kit_rows_and_final(result, our_group=our_group)
    ours = build_proposal(result.game_id, result.game_uid, final, rows)
    return exchange_result_agreement(channel, ours, budget=budget)
