"""Compose the external-service dependencies used by the production runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from common.config import ConfigError
from police_peer.strategy.hint_types import TextProvider
from police_peer.wire.config import PrivateConfig
from police_peer.wire.gmail_composition import GmailKitReporter, compose_gmail_reporter
from police_peer.wire.llm_composition import compose_external_gatekeeper, compose_text_provider


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    """The optional hint provider and counted-series Gmail reporter."""

    text_provider: TextProvider | None
    gmail_reporter: GmailKitReporter | None


def compose_runtime_services(
    private: PrivateConfig,
    shared_config: Mapping[str, object],
    *,
    mode: str,
    artifacts_dir: Path | str | None,
    emit_kit_bundle: bool,
    email_recipient: str | None,
    authorize_email_send: bool,
) -> RuntimeServices:
    """Build one shared Gatekeeper and both optional production adapters."""
    email_enabled = mode == "counted" and private.email.mode != "off"
    gatekeeper = (
        compose_external_gatekeeper(shared_config)
        if private.llm.provider == "openrouter" or email_enabled else None
    )
    text_provider = compose_text_provider(private.llm, shared_config, gatekeeper=gatekeeper)
    gmail_reporter = None
    if email_enabled:
        if artifacts_dir is None or not emit_kit_bundle:
            raise ConfigError(
                "counted Gmail reporting requires --artifacts-dir and --emit-kit-bundle"
            )
        if gatekeeper is None:  # pragma: no cover - implied by email_enabled
            raise ConfigError("counted Gmail reporting requires the external-service Gatekeeper")
        gmail_reporter = compose_gmail_reporter(
            private.email, artifacts_dir, gatekeeper,
            recipient=email_recipient, authorize_send=authorize_email_send,
        )
    return RuntimeServices(text_provider, gmail_reporter)


def report_counted_result(
    services: RuntimeServices, result_path: Path | None, *, mode: str,
) -> bool:
    """Report a counted result when enabled; return false when publication failed."""
    if mode != "counted" or services.gmail_reporter is None:
        return True
    if result_path is None:
        return False
    services.gmail_reporter.report(result_path)
    return True
