"""Send a kit-format series result email to a custom address (offline utility).

This is a standalone, opt-in development tool. It reads one league-kit ``result_<game_id>.json``
from an emitted kit bundle and sends it in the exact kit email format (SPEC §6.1, WARNINGS §6):

* the MIME **text body** is the canonical compact bytes of the result
  (``common.transport.canonical.canonical_bytes``: ``sort_keys=True, ensure_ascii=False,
  separators=(",", ":")``) -- never a pretty-printed re-serialization;
* there is exactly **one** attached file, the same result, named ``result_<game_id>.json``;
* the declaration/config/log artifacts are NOT emailed (they are published in the repo).

It builds a real Gmail client from local OAuth credentials. It never reads a secret into an
artifact and never auto-loads ``.env`` -- you pass paths or export ``GMAIL_OAUTH_CLIENT_FILE`` /
``GMAIL_OAUTH_TOKEN_FILE``. Use ``--dry-run`` to compose the MIME message and print it without
sending.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: OAuth scope must be send-only (App. E rule 30).
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

_DEFAULT_CLIENT = Path.cwd() / "credentials.json"
_DEFAULT_TOKEN = Path.cwd() / "token.json"


def _load_service(*, client_file: Path, token_file: Path) -> Any:
    """Build a Gmail API service client from local OAuth files.

    Reuses an existing ``token.json`` when present (refresh-token flow); otherwise runs the
    installed-app consent flow once and persists a refresh token. Credentials stay local and are
    never written into an artifact or printed.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_file.exists():
        # Inspect the STORED scopes directly -- ``from_authorized_user_file(..., scopes=...)``
        # overwrites ``creds.scopes`` with the argument, so it cannot tell us what the token was
        # actually granted. A token granted wider/different scopes (e.g. gmail.modify) cannot be
        # narrowed to send-only without re-consent, so force a fresh flow in that case.
        stored_scopes = json.loads(token_file.read_text(encoding="utf-8")).get("scopes") or []
        stored_scopes = {s.rstrip("/") for s in stored_scopes}
        if GMAIL_SEND_SCOPE in stored_scopes:
            creds = Credentials.from_authorized_user_file(str(token_file), [GMAIL_SEND_SCOPE])
    if creds is None or not creds.valid:
        if creds is not None and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_file), [GMAIL_SEND_SCOPE])
            creds = flow.run_local_server(port=0, prompt="consent")
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def _canonical_body(result: dict) -> bytes:
    """The exact canonical compact bytes the kit requires (SPEC section 2)."""
    import json as _json

    return _json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_message(*, sender: str, recipient: str, subject: str, result: dict, filename: str):
    """Return (EmailMessage, url-safe base64 raw) for a kit-format result email (no I/O)."""
    from email.message import EmailMessage

    body_bytes = _canonical_body(result)
    # ``EmailMessage.set_content`` appends one trailing newline to the text/plain body; accepted.
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body_bytes.decode("utf-8"))
    msg.add_attachment(body_bytes, maintype="application", subtype="json", filename=filename)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return msg, raw


def send_kit_result(
    *,
    result_path: Path,
    recipient: str,
    sender: str,
    game_uid: str,
    client_file: Path,
    token_file: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Send one kit result in kit format; return the Gmail response (or summaries on dry-run)."""
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not game_uid:
        game_uid = str(result.get("game_uid", ""))
    filename = result_path.name  # already ``result_<game_id>.json``
    subject = f"[PoliceThief-Report] Series {game_uid}"
    msg, raw = build_message(sender=sender, recipient=recipient, subject=subject, result=result,
                             filename=filename)

    print(f"Recipient: {recipient}\nSubject: {subject}\nAttachment: {filename}\n"
          f"Canonical body: {len(_canonical_body(result))} bytes")

    if dry_run:
        print("DRY-RUN -- composed message, not sent:\n")
        print(msg.as_string())
        return {"dry_run": True, "raw_length": len(raw)}

    service = _load_service(client_file=client_file, token_file=token_file)
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    print(f"Sent. Gmail message id: {sent.get('id')}")
    return sent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Path to the kit result_<game_id>.json to send")
    parser.add_argument("--to", required=True, help="Custom recipient email address")
    parser.add_argument("--from-address", default="peer@local", help="From header (MIME only)",
                        dest="from_address")
    parser.add_argument("--game-uid", default="", help="Game UID for the subject (default: result's)")
    parser.add_argument("--client-file", type=Path, default=_DEFAULT_CLIENT,
                        help="Path to credentials.json")
    parser.add_argument("--token-file", type=Path, default=_DEFAULT_TOKEN,
                        help="Path to token.json")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print, do not send")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.result.is_file():
        print(f"ERROR: result file not found: {args.result}", file=sys.stderr)
        return 2
    try:
        send_kit_result(
            result_path=args.result,
            recipient=args.to,
            sender=args.from_address,
            game_uid=args.game_uid,
            client_file=args.client_file,
            token_file=args.token_file,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 -- a dev tool surfaces the cause plainly
        logger.exception("send failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
