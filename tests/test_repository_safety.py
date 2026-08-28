"""Tests for tracked secret and archive checks."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_no_secrets  # noqa: E402
import check_source_archives  # noqa: E402
from helpers import initialize_git_repository, track  # noqa: E402


def secret_config() -> dict[str, object]:
    """Return a minimal secret-check policy."""
    return {
        "secret_allowed_paths": [".env.example"],
        "secret_banned_names": [".env", "credentials.json", "token.json"],
        "secret_banned_globs": [
            ".env.*", "*credentials*.json", "*token*.json", "*.pem",
        ],
    }


def archive_config(allowlist: list[str] | None = None) -> dict[str, object]:
    """Return a minimal archive-check policy."""
    return {
        "archive_suffixes": [".zip", ".tar.gz"],
        "archive_allowlist": allowlist or [],
    }


class RepositorySafetyTests(unittest.TestCase):
    """Exercise tracked-file safety checks in temporary Git repositories."""

    def test_secret_check_flags_banned_tracked_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            (repo / ".env").write_text("TOKEN=hidden\n", encoding="utf-8")
            track(repo, ".env")
            self.assertEqual(
                check_no_secrets.scan_repository(repo, secret_config()),
                ["tracked secret-like file: .env"],
            )

    def test_secret_check_allows_example_and_flags_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            (repo / ".env.example").write_text("API_KEY=replace-me\n", encoding="utf-8")
            token = "sk-" + "A" * 24
            (repo / "settings.py").write_text(f'KEY = "{token}"\n', encoding="utf-8")
            track(repo, ".env.example", "settings.py")
            self.assertEqual(
                check_no_secrets.scan_repository(repo, secret_config()),
                ["prefixed API token: settings.py:1"],
            )

    def test_secret_check_flags_variant_oauth_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            for name in ("oauth-credentials-prod.json", "gmail-token-prod.json"):
                (repo / name).write_text("{}\n", encoding="utf-8")
            track(repo, "oauth-credentials-prod.json", "gmail-token-prod.json")
            self.assertEqual(
                check_no_secrets.scan_repository(repo, secret_config()),
                [
                    "tracked secret-like file: gmail-token-prod.json",
                    "tracked secret-like file: oauth-credentials-prod.json",
                ],
            )

    def test_secret_check_skips_binary_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            (repo / "data.bin").write_bytes(b"\0" + ("sk-" + "A" * 24).encode())
            track(repo, "data.bin")
            self.assertEqual(check_no_secrets.scan_repository(repo, secret_config()), [])

    def test_mail_preview_helper_has_no_live_google_send_path(self) -> None:
        source = (ROOT / "scripts" / "send_kit_email.py").read_text(encoding="utf-8")
        self.assertIn("GMAIL_TEST_RECIPIENT", source)
        self.assertNotIn("googleapiclient", source)
        self.assertNotIn(".messages().send", source)

    def test_archive_check_rejects_unexpected_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            (repo / "bundle.zip").write_bytes(b"archive")
            track(repo, "bundle.zip")
            self.assertEqual(
                check_source_archives.unexpected_archives(repo, archive_config()),
                ["bundle.zip"],
            )

    def test_archive_check_honors_exact_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialize_git_repository(Path(directory))
            (repo / "fixture.tar.gz").write_bytes(b"archive")
            track(repo, "fixture.tar.gz")
            self.assertEqual(
                check_source_archives.unexpected_archives(repo, archive_config(["fixture.tar.gz"])),
                [],
            )


if __name__ == "__main__":
    unittest.main()
