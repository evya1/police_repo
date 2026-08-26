"""Offline proof that LLM usage reaches reporting without gaining game authority."""

from __future__ import annotations

import json
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path

from common.domain.scoring import Role
from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_documents import build_result
from common.transport.kit_names import result_name
from common.transport.kit_settlement import series_final
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.infra.llm_client import RawCompletion
from police_peer.sdk import create_peer
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import EmailSettings


class _RecordingGatekeeper(ExternalApiGatekeeper):
    def __init__(self) -> None:
        super().__init__()
        self.lanes: list[str] = []

    def execute(self, call, *args, lane="reporting", **kwargs):
        self.lanes.append(lane)
        return super().execute(call, *args, lane=lane, **kwargs)


class _Completion:
    wording = "Near the agreed landmark."

    def complete(self, prompt: str, *, deadline: float | None) -> RawCompletion:
        match = re.search(r"landmark=([^;\n]+)", prompt)
        assert match is not None and deadline is not None
        self.wording = f"Near {match.group(1)}."
        return RawCompletion(
            text=self.wording, provider="Novita", model="actual/model",
            input_tokens=17, output_tokens=4,
        )


def _private(path: Path) -> Path:
    path.write_text(
        "[llm]\nprovider = \"openrouter\"\n"
        "model = \"inclusionai/ling-3.0-flash\"\nprovider_slug = \"novita\"\n"
        "step_deadline_seconds = 5\nmax_output_tokens = 8\nevery_n_steps = 1\n",
        encoding="utf-8",
    )
    return path


def _result_document(tokens: int) -> dict:
    game_id, game_uid = "group-a-vs-group-b", "00000000-0000-0000-0000-000000000002"
    groups = ("group-a", "group-b")
    rows = []
    for number in range(1, 7):
        rows.append(
            {
                "sub_game_number": number,
                "roles": {groups[0]: "police", groups[1]: "thief"},
                "result": "capture", "winner_group": groups[0], "tie": False, "steps": 1,
                "started_at": f"2026-08-26T12:{number:02d}:00+03:00",
                "ended_at": f"2026-08-26T12:{number:02d}:01+03:00",
                "github_commit": {groups[0]: "a" * 40, groups[1]: "b" * 40},
                "tokens": {groups[0]: tokens if number == 1 else 0, groups[1]: 0},
                "score": {groups[0]: 100, groups[1]: 0},
                "log_files": dict.fromkeys(groups, f"log_{game_id}_g{number:02d}.json"),
                "audit": {"log_verified": True, "tampered": False},
            }
        )
    final = series_final(rows, groups, counted=True)
    return build_result(
        game_id=game_id, game_uid=game_uid, groups=list(groups), sub_games=rows,
        final_result=final,
        mutual_agreement=mutual_agreement(game_id, final, rows, confirmed=True),
    )


def test_llm_usage_reaches_agreed_result_and_reporting_lane(tmp_path: Path) -> None:
    config = Path(__file__).resolve().parents[2] / "config" / "game.json"
    gatekeeper, completion = _RecordingGatekeeper(), _Completion()
    facade = create_peer(
        config, private_config_path=_private(tmp_path / "game.toml"),
        role=Role.POLICE, group_id="group-a", gatekeeper=gatekeeper,
        environment={"OPENROUTER_API_KEY": "unit-only-credential"},
        completion_client=completion,
    )
    facade.engine.start_subgame(1, Role.POLICE, terms=facade.config.terms)
    decision = facade.engine.decide()
    total = facade.engine.token_ledger.series_total(include_warmup=True)
    assert decision["hint"] and (total.input_tokens, total.output_tokens) == (17, 4)

    document = _result_document(total.input_tokens + total.output_tokens)
    path = tmp_path / result_name(document["game_id"])
    path.write_text(json.dumps(document), encoding="utf-8")
    reporter = compose_gmail_reporter(
        EmailSettings("recipient@example.invalid", "dry-run"), tmp_path, gatekeeper,
    )
    receipt = reporter.report(path)

    outbox = tmp_path / "outbox" / document["game_uid"]
    message = BytesParser(policy=policy.default).parsebytes((outbox / "message.eml").read_bytes())
    (attachment,) = message.iter_attachments()
    persisted = path.read_text(encoding="utf-8") + (outbox / "receipt.json").read_text()
    assert document["final_result"]["tokens_total_series"]["group-a"] == 21
    assert gatekeeper.lanes == ["llm", "reporting"]
    assert attachment.get_payload(decode=True) == path.read_bytes()
    assert receipt.gmail_api_contacted is False
    assert completion.wording not in persisted and "unit-only-credential" not in persisted
