from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common.transport.kit_agreement import AgreementOutcome, assert_reportable
from police_peer.reporting.artifacts import ReportingArtifactBundle
from police_peer.reporting.gmail import GmailSender
from police_peer.reporting.schemas import ArtifactError, SeriesResult


class ReportingPipelineError(Exception):
    """Raised when report assembly or pipeline validation fails."""


class SentReportsStore:
    """Durable sent-reports store persisted to a JSON file.

    Replaces the in-memory set so idempotency survives process restart.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(".sent_reports.json")
        self._cache: set[str] = self._load()

    def _load(self) -> set[str]:
        if self._path.exists():
            try:
                return set(json.loads(self._path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, TypeError):
                return set()
        return set()

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(sorted(self._cache)), encoding="utf-8"
        )

    def is_sent(self, game_uid: str) -> bool:
        return game_uid in self._cache

    def mark_sent(self, game_uid: str) -> None:
        self._cache.add(game_uid)
        self._save()


def settle_series(
    our_result: SeriesResult, their_result: SeriesResult
) -> SeriesResult | None:
    """Conservative settlement guard (OPEN-004).

    Only mutually complete and consistent reports can settle. Missing,
    incomplete, or conflicting evidence stays explicitly unsettled — no
    sanction is invented locally. Returns the settled result on agreement,
    or None when the peers disagree.
    """
    if (
        our_result.total_police_score == their_result.total_police_score
        and our_result.total_thief_score == their_result.total_thief_score
        and our_result.tie_applied == their_result.tie_applied
    ):
        return our_result  # both peers agree — settled
    return None  # disagreement or incomplete — unsettled


class KitInteropAdapter:
    """Adapter converting internal T032 artifacts to kit-compatible filenames/IDs.

    INTERNAL/INTEROP — NOT OFFICIAL. T016 (official Moodle templates) remains
    OPEN. This adapter maps internal-1 schema artifacts to the kit profile at
    a single boundary, distinct from the internal T032 schemas. The official
    templates replace this adapter when they arrive.
    """

    @staticmethod
    def to_kit_filename(artifact: Any) -> str:
        """Map internal artifact to kit-compatible filename."""
        kind = getattr(artifact, "kind", "artifact")
        game_uid = getattr(artifact, "game_uid", "")
        game_id = getattr(artifact, "game_id", None)
        suffix = game_id if game_id else "series"
        return f"{kind}_{game_uid}_{suffix}.json"


class ReportingPipeline:
    """End-to-end signed reporting pipeline assembling artifacts and transmitting via Gmail."""

    def __init__(
        self,
        gmail_sender: GmailSender,
        sent_reports_store: SentReportsStore | None = None,
    ) -> None:
        self.gmail_sender = gmail_sender
        self._sent_reports = sent_reports_store or SentReportsStore()

    def process_and_send(
        self,
        bundle: ReportingArtifactBundle,
        *,
        agreement: AgreementOutcome,
        counted: bool = True,
        recipient: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        # Nothing leaves without a mutual agreement. Two contradictory counted reports score
        # zero for BOTH teams (App. E rule 35), so the side that cannot confirm a shared
        # result declines to send rather than reporting alone and taking its opponent down.
        assert_reportable(agreement, counted=counted)
        game_uid = bundle.declaration.game_uid
        if self._sent_reports.is_sent(game_uid):
            raise ReportingPipelineError(f"Series report for '{game_uid}' has already been processed.")

        # Reconcile, validate entire bundle, and assemble attachments
        try:
            bundle.validate_bundle()
            attachments = bundle.to_attachments()
        except ArtifactError as exc:
            raise ReportingPipelineError(f"Bundle reconciliation failed: {exc}") from exc

        # Transmit strictly through send-only Gmail adapter behind Gatekeeper
        try:
            result = self.gmail_sender.send_report(
                game_uid=game_uid,
                artifacts=attachments,
                recipient=recipient,
                subject=subject,
            )
        except Exception as exc:
            raise ReportingPipelineError(f"Report transmission failed: {exc}") from exc

        self._sent_reports.mark_sent(game_uid)
        return result
