"""Production SDK/runner composition reaches the typed adapter and preserves gameplay."""

from __future__ import annotations

import json
import re
from pathlib import Path

from common.domain.scoring import Outcome, Role
from common.transport.series import SeriesResult
from police_peer.infra.llm_client import RawCompletion
from police_peer.infra.openrouter_client import OpenRouterConnectionError
from police_peer.reporting.runtime_artifacts import write_artifacts
from police_peer.runner import run_one_peer
from police_peer.sdk import create_peer


class _ScriptedClient:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def complete(self, prompt: str, *, deadline: float | None) -> RawCompletion:
        self.calls.append(prompt)
        if self.fail:
            raise OpenRouterConnectionError("scripted outage")
        landmark = re.search(r"landmark=([^;\n]+)", prompt)
        assert landmark is not None
        return RawCompletion(
            text=f"Near {landmark.group(1)}.", provider="Novita", model="actual/model",
            input_tokens=17, output_tokens=4,
        )


def _private(path: Path, provider: str = "openrouter") -> Path:
    path.write_text(
        "[llm]\n"
        f'provider = "{provider}"\n'
        'model = "inclusionai/ling-3.0-flash"\n'
        'provider_slug = "novita"\n'
        "step_deadline_seconds = 5\nmax_output_tokens = 8\nevery_n_steps = 1\n",
        encoding="utf-8",
    )
    return path


def _shared() -> dict:
    path = Path(__file__).resolve().parents[2] / "config" / "game.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _one_turn(config: dict, private: Path, client: _ScriptedClient):
    facade = create_peer(
        config, private_config_path=private, role=Role.POLICE, group_id="p",
        environment={"OPENROUTER_API_KEY": "unit-credential"}, completion_client=client,
    )
    facade.engine.start_subgame(1, Role.POLICE, terms=facade.config.terms)
    return facade, facade.engine.decide()


def test_sdk_composition_reaches_openrouter_adapter_and_ledger(
    tmp_path: Path,
) -> None:
    client = _ScriptedClient()
    facade, result = _one_turn(_shared(), _private(tmp_path / "game.toml"), client)
    assert client.calls and result["hint"]
    total = facade.engine.token_ledger.series_total(include_warmup=True)
    assert (total.input_tokens, total.output_tokens) == (17, 4)


def test_provider_failure_preserves_deterministic_move_barrier_and_verdict(
    tmp_path: Path,
) -> None:
    private = _private(tmp_path / "game.toml")
    _, success = _one_turn(_shared(), private, _ScriptedClient())
    failed_facade, failed = _one_turn(_shared(), private, _ScriptedClient(fail=True))
    assert (success["move"], success["barrier_cell"], success["verdict"]) == (
        failed["move"], failed["barrier_cell"], failed["verdict"],
    )
    total = failed_facade.engine.token_ledger.series_total(include_warmup=True)
    assert total.status.value == "unknown"


def test_composition_credential_never_enters_logs_or_artifacts(caplog, tmp_path: Path) -> None:
    credential = "unit-credential-never-persist"
    create_peer(
        _shared(), private_config_path=_private(tmp_path / "game.toml"),
        environment={"OPENROUTER_API_KEY": credential}, completion_client=_ScriptedClient(),
    )
    artifacts = tmp_path / "artifacts"
    write_artifacts(artifacts, SeriesResult("g", "u"))
    persisted = "".join(path.read_text("utf-8") for path in artifacts.iterdir())
    assert credential not in caplog.text and credential not in persisted


def test_cli_runner_passes_composed_provider_into_sdk(
    monkeypatch, tmp_path: Path,
) -> None:
    import police_peer.runner as runner

    shared = tmp_path / "game.json"
    shared.write_text(json.dumps(_shared()), encoding="utf-8")
    provider = object()
    seen = {}

    class _Channel:
        def __init__(self, *_args, **_kwargs):
            pass

        def close(self):
            pass

    class _Facade:
        def run(self):
            return SeriesResult("g", "u", ledger=[], settled=False,
                                settled_outcome=Outcome.TAMPER_FORFEIT)

    monkeypatch.setattr(runner, "compose_text_provider", lambda *_a, **_k: provider)
    monkeypatch.setattr(runner, "serve_background", lambda *_a, **_k: None)
    monkeypatch.setattr(runner, "edge_answers", lambda *_a, **_k: True)
    monkeypatch.setattr(runner, "McpChannel", _Channel)

    def create(**kwargs):
        seen.update(kwargs)
        return _Facade()

    monkeypatch.setattr(runner, "create_peer", create)
    rc = run_one_peer(
        shared_config=shared, private_config=_private(tmp_path / "private.toml", "template"),
        connect_timeout=0.1,
    )
    assert rc == 6
    assert seen["text_provider"] is provider


def test_missing_key_refuses_runner_before_server_start(
    monkeypatch, tmp_path: Path,
) -> None:
    import police_peer.runner as runner

    shared = tmp_path / "game.json"
    shared.write_text(json.dumps(_shared()), encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(
        runner, "serve_background",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("server started")),
    )
    assert run_one_peer(
        shared_config=shared, private_config=_private(tmp_path / "private.toml"),
    ) == 2
