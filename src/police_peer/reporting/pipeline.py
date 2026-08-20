from __future__ import annotations

from typing import Any

from police_peer.reporting.artifacts import ReportingArtifactBundle
from police_peer.reporting.gmail import GmailSender
from police_peer.reporting.schemas import SchemaError


class ReportingPipelineError(Exception):
    """Raised when report assembly or pipeline validation fails."""


class ReportingPipeline:
    """End-to-end signed reporting pipeline assembling artifacts and transmitting via Gmail."""

    def __init__(self, gmail_sender: GmailSender) -> None:
        self.gmail_sender = gmail_sender
        self._sent_reports: set[str] = set()

    def process_and_send(
        self,
        bundle: ReportingArtifactBundle,
        *,
        recipient: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        game_uid = bundle.declaration.game_uid
        if game_uid in self._sent_reports:
            raise ReportingPipelineError(f"Series report for '{game_uid}' has already been processed.")

        # Reconcile & validate entire bundle
        try:
            bundle.validate_bundle()
        except SchemaError as exc:
            raise ReportingPipelineError(f"Bundle reconciliation failed: {exc}") from exc

        # Assemble exact canonical attachment bytes
        attachments = bundle.to_attachments()

        # Transmit strictly through send-only Gmail adapter behind Gatekeeper
        result = self.gmail_sender.send_report(
            game_uid=game_uid,
            artifacts=attachments,
            recipient=recipient,
            subject=subject,
        )

        self._sent_reports.add(game_uid)
        return result
