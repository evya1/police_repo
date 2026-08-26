"""Stored Gmail OAuth metadata is checked without exposing credential values."""

from __future__ import annotations

import json

import pytest

from common.config import ConfigError
from police_peer.infra.gmail_oauth import _validate_stored_token_scope
from police_peer.reporting.gmail import GMAIL_SEND_SCOPE


def _token_file(tmp_path, scopes):
    path = tmp_path / "token.json"
    path.write_text(json.dumps({"scopes": scopes, "refresh_token": "not-inspected"}))
    return path


def test_exact_send_only_scope_is_accepted(tmp_path) -> None:
    _validate_stored_token_scope(_token_file(tmp_path, [GMAIL_SEND_SCOPE]))


@pytest.mark.parametrize(
    "scopes",
    [
        [],
        ["https://www.googleapis.com/auth/gmail.modify"],
        [GMAIL_SEND_SCOPE, "https://www.googleapis.com/auth/gmail.readonly"],
    ],
)
def test_missing_or_broader_stored_scope_is_rejected(tmp_path, scopes) -> None:
    with pytest.raises(ConfigError, match="send-only"):
        _validate_stored_token_scope(_token_file(tmp_path, scopes))


def test_malformed_token_metadata_is_rejected_without_echoing_path(tmp_path) -> None:
    path = tmp_path / "sensitive-token-name.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError, match="metadata") as captured:
        _validate_stored_token_scope(path)
    assert str(path) not in str(captured.value)
