from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from police_peer import runner
from police_peer.evidence.token_ledger import TokenLedger


class _Channel:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def close(self) -> None:
        pass


class _Facade:
    def run(self):
        return SimpleNamespace(settled=True, opponent_identity={})


class _Reporter:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def report(self, path: Path) -> None:
        self.paths.append(path)


def test_counted_runner_shares_gatekeeper_and_reports_published_result(
    monkeypatch, tmp_path: Path,
) -> None:
    marker, reporter = object(), _Reporter()
    seen: dict[str, object] = {}
    result_path = tmp_path / "kit" / "result.json"
    monkeypatch.setattr(runner, "serve_background", lambda *a, **k: None)
    monkeypatch.setattr(runner, "edge_answers", lambda *a, **k: True)
    monkeypatch.setattr(runner, "McpChannel", _Channel)
    monkeypatch.setattr(runner, "create_peer", lambda **kwargs: _Facade())
    monkeypatch.setattr(runner, "compose_external_gatekeeper", lambda config: marker)
    monkeypatch.setattr(
        runner, "compose_text_provider",
        lambda settings, config, gatekeeper: seen.setdefault("llm_gatekeeper", gatekeeper),
    )

    def compose_email(settings, root, gatekeeper, **kwargs):
        seen["gmail_gatekeeper"] = gatekeeper
        seen["recipient"] = kwargs["recipient"]
        return reporter

    monkeypatch.setattr(runner, "compose_gmail_reporter", compose_email)
    monkeypatch.setattr(
        runner, "prepare_runtime_evidence",
        lambda **kwargs: SimpleNamespace(
            greeting_identity={}, identity=None, token_ledger=TokenLedger(),
        ),
    )
    monkeypatch.setattr(runner, "assert_counted_eligible", lambda ledger: None)
    monkeypatch.setattr(
        runner, "settle", lambda *a, **k: SimpleNamespace(agreed=True, reason="agreed"),
    )
    monkeypatch.setattr(runner, "write_artifacts", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_publish_replay_bundle", lambda *a, **k: None)
    monkeypatch.setattr(runner, "publish_kit", lambda *a, **k: result_path)

    code = runner.run_one_peer(
        mode="counted", artifacts_dir=tmp_path, email_recipient="recipient@example.invalid",
    )
    assert code == 0
    assert seen == {
        "llm_gatekeeper": marker,
        "gmail_gatekeeper": marker,
        "recipient": "recipient@example.invalid",
    }
    assert reporter.paths == [result_path]
