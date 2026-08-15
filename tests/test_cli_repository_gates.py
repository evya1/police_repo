"""Command-level tests for repository-state gates and the suite runner."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_line_cap  # noqa: E402
import check_no_secrets  # noqa: E402
import check_source_archives  # noqa: E402
import quality_common  # noqa: E402
import run_quality_gates  # noqa: E402
from helpers import captured_main, initialize_git_repository, track  # noqa: E402


class RepositoryGateCliTests(unittest.TestCase):
    """Exercise tracked-file and runner command paths."""

    def test_secret_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = initialize_git_repository(Path(directory))
            config = root / "quality.toml"
            config.write_text(
                'secret_allowed_paths = []\nsecret_banned_names = [".env"]\n'
                'secret_banned_globs = ["*.pem"]\n',
                encoding="utf-8",
            )
            (root / "safe.txt").write_text("safe\n", encoding="utf-8")
            track(root, "safe.txt")
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_no_secrets.main, arguments)[0], 0)
            (root / ".env").write_text("hidden\n", encoding="utf-8")
            track(root, ".env")
            self.assertEqual(captured_main(check_no_secrets.main, arguments)[0], 1)

    def test_archive_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = initialize_git_repository(Path(directory))
            config = root / "quality.toml"
            config.write_text(
                'archive_suffixes = [".zip"]\narchive_allowlist = []\n', encoding="utf-8"
            )
            (root / "safe.txt").write_text("safe\n", encoding="utf-8")
            track(root, "safe.txt")
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_source_archives.main, arguments)[0], 0)
            (root / "bundle.zip").write_bytes(b"archive")
            track(root, "bundle.zip")
            self.assertEqual(captured_main(check_source_archives.main, arguments)[0], 1)

    def test_line_main_success_and_empty_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            source.mkdir()
            (source / "app.py").write_text("value = 1\n", encoding="utf-8")
            config = root / "quality.toml"
            config.write_text(
                'line_limit = 150\nline_mode = "logical"\nsource_dirs = ["src"]\n'
                'test_dirs = []\nscript_dirs = []\ncode_extensions = [".py"]\n'
                "exclude_dirs = []\n",
                encoding="utf-8",
            )
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_line_cap.main, arguments)[0], 0)
            (source / "app.py").unlink()
            self.assertEqual(captured_main(check_line_cap.main, arguments)[0], 1)

    def test_common_configuration_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(quality_common.QualityError):
                quality_common.load_config(root, Path("missing.toml"))
            invalid = root / "invalid.toml"
            invalid.write_text("broken = [\n", encoding="utf-8")
            with self.assertRaises(quality_common.QualityError):
                quality_common.load_config(root, invalid)
            with self.assertRaises(quality_common.QualityError):
                quality_common.tracked_files(root)
            with self.assertRaises(quality_common.QualityError):
                quality_common.safe_repo_path(root, "../outside")

    def test_runner_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(run_quality_gates, "run_checks", return_value=[]):
                self.assertEqual(run_quality_gates.main(["--repo", str(root)]), 0)
            with mock.patch.object(
                run_quality_gates, "run_checks", return_value=["check_docs_present.py"]
            ):
                self.assertEqual(run_quality_gates.main(["--repo", str(root)]), 1)


if __name__ == "__main__":
    unittest.main()
