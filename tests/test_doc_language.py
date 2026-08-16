"""Tests for the documentation-language gate."""

from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_doc_language  # noqa: E402
from helpers import captured_main, initialize_git_repository, track  # noqa: E402

CONFIG = textwrap.dedent(
    """
    doc_language_paths = ["docs", "README.md"]
    doc_language_allowlist = ["docs/spec/CANONICAL_REQUIREMENTS.md"]
    doc_language_allowed_literals = ["reference-v3"]
    doc_language_patterns = [
      "\\\\breference implementation\\\\w*",
      "\\\\bvendored\\\\b",
    ]
    """
).strip()


def _repo(directory: str) -> Path:
    root = initialize_git_repository(Path(directory))
    (root / "config").mkdir()
    (root / "config" / "quality.toml").write_text(CONFIG, encoding="utf-8")
    (root / "docs" / "spec").mkdir(parents=True)
    return root


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    track(root, relative)


class MaskLiteralTests(unittest.TestCase):
    """Exact protocol literals must never trigger a prose pattern."""

    def test_masking_replaces_every_configured_literal(self) -> None:
        masked = check_doc_language.mask_literals("wire_shape: reference-v3 here", ["reference-v3"])
        self.assertNotIn("reference-v3", masked)
        self.assertIn("wire_shape:", masked)

    def test_masking_leaves_unrelated_text_alone(self) -> None:
        self.assertEqual(check_doc_language.mask_literals("plain text", ["reference-v3"]), "plain text")


class ScanTests(unittest.TestCase):
    """File scanning reports line numbers and the matched text."""

    def test_scan_reports_line_and_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "doc.md"
            path.write_text("clean line\nthis was vendored\n", encoding="utf-8")
            findings = check_doc_language.scan_file(path, check_doc_language._compiled([r"\bvendored\b"]), [])
        self.assertEqual([(number, text) for number, text, _ in findings], [(2, "vendored")])

    def test_unreadable_file_yields_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent.md"
            self.assertEqual(check_doc_language.scan_file(missing, [], []), [])

    def test_invalid_pattern_is_reported_as_configuration_error(self) -> None:
        with self.assertRaises(check_doc_language.QualityError):
            check_doc_language._compiled(["("])


class GateTests(unittest.TestCase):
    """End-to-end behaviour of the command."""

    def test_clean_documentation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _repo(directory)
            _write(root, "docs/PLAN.md", "The selected profile is `reference-v3`.\n")
            code, output = captured_main(
                check_doc_language.main, ["--repo", str(root), "--config", "config/quality.toml"]
            )
        self.assertEqual(code, 0)
        self.assertIn("OK", output)

    def test_offending_wording_fails_and_names_the_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _repo(directory)
            _write(root, "docs/PLAN.md", "ok\nthe reference implementation defines this\n")
            code, output = captured_main(
                check_doc_language.main, ["--repo", str(root), "--config", "config/quality.toml"]
            )
        self.assertEqual(code, 1)
        self.assertIn("docs/PLAN.md:2", output)
        self.assertIn("reference implementation", output)

    def test_allowlisted_and_out_of_scope_files_are_not_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _repo(directory)
            _write(root, "docs/spec/CANONICAL_REQUIREMENTS.md", "vendored\n")
            _write(root, "notes.md", "vendored\n")
            code, _ = captured_main(
                check_doc_language.main, ["--repo", str(root), "--config", "config/quality.toml"]
            )
        self.assertEqual(code, 0)

    def test_missing_configuration_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = initialize_git_repository(Path(directory))
            code, output = captured_main(
                check_doc_language.main, ["--repo", str(root), "--config", "absent.toml"]
            )
        self.assertEqual(code, 1)
        self.assertIn("FAIL", output)


if __name__ == "__main__":
    unittest.main()
