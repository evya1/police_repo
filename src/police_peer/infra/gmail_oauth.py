"""Build the production Gmail client from explicit local OAuth files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from common.config import ConfigError
from police_peer.reporting.gmail import GMAIL_SEND_SCOPE, validate_oauth_scope


def build_gmail_service(*, client_file: Path, token_file: Path) -> Any:
    """Return a Gmail v1 client authorized with exactly ``gmail.send``.

    ``client_file`` is the downloaded desktop OAuth client JSON. ``token_file`` is the
    ignored local authorized-user token, created or refreshed by this function. Neither
    path nor any credential content is included in raised configuration errors.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - locked production dependency
        raise ConfigError("Gmail OAuth dependencies are not installed") from exc

    credentials = None
    try:
        if token_file.is_file():
            _validate_stored_token_scope(token_file)
            credentials = Credentials.from_authorized_user_file(
                str(token_file), [GMAIL_SEND_SCOPE]
            )
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                if not client_file.is_file():
                    raise ConfigError("Gmail OAuth client file is not available")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_file), [GMAIL_SEND_SCOPE]
                )
                credentials = flow.run_local_server(port=0)
            _write_private_token(token_file, credentials.to_json())
        granted = credentials.granted_scopes or credentials.scopes
        validate_oauth_scope(list(granted) if granted else None)
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except ConfigError:
        raise
    except Exception as exc:
        raise ConfigError("Gmail OAuth client initialization failed") from exc


def _validate_stored_token_scope(path: Path) -> None:
    """Reject token metadata that was not granted exactly the send-only scope."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        scopes = document.get("scopes") if isinstance(document, dict) else None
    except (OSError, ValueError) as exc:
        raise ConfigError("Gmail OAuth token metadata is invalid") from exc
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
        raise ConfigError("Gmail OAuth token must declare the send-only scope")
    normalized = {scope.rstrip("/") for scope in scopes}
    if normalized != {GMAIL_SEND_SCOPE}:
        raise ConfigError("Gmail OAuth token must declare the send-only scope")


def _write_private_token(path: Path, payload: str) -> None:
    """Atomically persist an OAuth token with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(path)
