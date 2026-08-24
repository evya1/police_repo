import pytest

from common.transport.kit_agreement import AgreementOutcome
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.artifacts import ReportingArtifactBundle
from police_peer.reporting.gmail import FileIdempotencyStore, GmailSender
from police_peer.reporting.pipeline import (
    ReportingPipeline,
    ReportingPipelineError,
    SentReportsStore,
)
from police_peer.reporting.schemas import (
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    finalize_log,
)

OFFICIAL_RECIPIENT = "rmisegal+uoh26finalgame@gmail.com"


class FakeGmailService:
    """Fake Gmail service for testing — no real OAuth or send."""

    def users(self):
        return self

    def messages(self):
        return FakeMessagesResource()


class FakeMessagesResource:
    def send(self, userId="me", body=None):  # noqa: N803
        return self

    def execute(self):
        return {"id": "12345", "status": "OK"}


def _signer(b: bytes) -> str:
    return "sig-" + b.hex()[:8]


def _sample_bundle(game_uid: str = "series-test-99"):
    decl = build_declaration(
        game_uid=game_uid, team="team_alpha", role="police", members=["alice", "bob"],
        police_repo_url="http://p", thief_repo_url="http://t", mcp_addresses=["mcp://1"],
        hardware="h", model="m", token_budget=1000, start_time="s", end_time="e", num_games=6,
    )

    configs = []
    logs = []
    subgame_results = []
    commits = {}
    tokens = {}

    for i in range(6):
        gid = f"{game_uid}:{i}"
        cfg = build_sub_game_config(
            game_uid=game_uid, game_id=gid, sub_game_index=i,
            role_for_this_sub_game="police" if i % 2 == 0 else "thief",
            agreed_terms={"seed": i}, git_commit=f"commit-{i}",
        )
        configs.append(cfg)

        log = build_sub_game_log(game_uid=game_uid, game_id=gid, steps=[{"step": i}])
        finalize_log(log, _signer)
        logs.append(log)

        subgame_results.append({"game_id": gid, "score": 10})
        commits[gid] = f"commit-{i}"
        tokens[gid] = 100

    res = build_series_result(
        game_uid=game_uid, sub_game_results=subgame_results, total_police_score=60,
        total_thief_score=30, tie_applied=False, repo_links={"police": "http://p"},
        total_llm_tokens_per_series=600, sub_game_git_commits=commits,
        total_llm_tokens_per_sub_game=tokens,
    )

    return ReportingArtifactBundle(
        declaration=decl, sub_game_configs=configs, sub_game_logs=logs, series_result=res,
    )


def test_reporting_pipeline_success_and_idempotence(tmp_path):
    bundle = _sample_bundle("series-good")
    attachments = bundle.to_attachments()
    assert len(attachments) == 14

    gk = ExternalApiGatekeeper()
    sender = GmailSender(
        gatekeeper=gk,
        default_recipient=OFFICIAL_RECIPIENT,
        scopes=["gmail.send"],
        service_client=FakeGmailService(),
        idempotency_store=FileIdempotencyStore(tmp_path / "gmail_sent.json"),
    )
    pipeline = ReportingPipeline(gmail_sender=sender, sent_reports_store=SentReportsStore(tmp_path / "sent.json"))

    agreed = AgreementOutcome(True, "both peers derived one consensus digest")
    receipt = pipeline.process_and_send(bundle, agreement=agreed)
    assert receipt["status"] == "OK"

    with pytest.raises(ReportingPipelineError, match="already been processed"):
        pipeline.process_and_send(bundle, agreement=agreed)


def test_reporting_pipeline_unfinalized_log_refusal(tmp_path):
    bundle = _sample_bundle("series-unfinalized")
    object.__setattr__(bundle.sub_game_logs[0], "finalized", False)

    gk = ExternalApiGatekeeper()
    sender = GmailSender(
        gatekeeper=gk,
        default_recipient=OFFICIAL_RECIPIENT,
        scopes=["gmail.send"],
        service_client=FakeGmailService(),
        idempotency_store=FileIdempotencyStore(tmp_path / "gmail_sent2.json"),
    )
    pipeline = ReportingPipeline(gmail_sender=sender, sent_reports_store=SentReportsStore(tmp_path / "sent2.json"))

    with pytest.raises(ReportingPipelineError, match="Bundle reconciliation failed"):
        pipeline.process_and_send(
            bundle, agreement=AgreementOutcome(True, "both peers derived one consensus digest")
        )


def test_reporting_pipeline_refuses_without_mutual_agreement(tmp_path):
    """W2-P5/CT-08: the pipeline never transmits a series the two peers never agreed on."""
    bundle = _sample_bundle("series-disagreed")

    gk = ExternalApiGatekeeper()
    sender = GmailSender(
        gatekeeper=gk,
        default_recipient=OFFICIAL_RECIPIENT,
        scopes=["gmail.send"],
        service_client=FakeGmailService(),
        idempotency_store=FileIdempotencyStore(tmp_path / "gmail_sent3.json"),
    )
    pipeline = ReportingPipeline(
        gmail_sender=sender, sent_reports_store=SentReportsStore(tmp_path / "sent3.json")
    )

    disagreed = AgreementOutcome(False, "no counter-proposal")
    with pytest.raises(ReportingPipelineError, match="no mutual result agreement"):
        pipeline.process_and_send(bundle, agreement=disagreed)
