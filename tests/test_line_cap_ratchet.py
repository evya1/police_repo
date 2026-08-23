"""Focused tests for the line-cap ratchet (T040): pinned per-file baseline over `source_dirs`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_line_cap  # noqa: E402
from helpers import captured_main  # noqa: E402

_BASE_CONFIG = (
    'line_limit = 150\nline_mode = "logical"\nsource_dirs = ["src"]\n'
    'test_dirs = []\nscript_dirs = []\ncode_extensions = [".py"]\nexclude_dirs = []\n'
)


def _write_repo(root: Path, big_lines: int, baseline_toml: str = "") -> Path:
    source = root / "src"
    source.mkdir()
    (source / "big.py").write_text("\n".join(f"x{i} = {i}" for i in range(big_lines)) + "\n", encoding="utf-8")
    config = root / "quality.toml"
    config.write_text(_BASE_CONFIG + baseline_toml, encoding="utf-8")
    return config


class LineCapRatchetTests(unittest.TestCase):
    """Every scenario the T040 ratchet must prove, run against a throwaway fixture repo."""

    def test_unlisted_violation_over_cap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(Path(directory), big_lines=200)
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("new unlisted violation", out)

    def test_exact_baseline_match_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=200,
                baseline_toml='\n[line_cap_baseline]\n"src/big.py" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 0)
            self.assertIn("1 baselined", out)

    def test_baseline_plus_one_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=201,
                baseline_toml='\n[line_cap_baseline]\n"src/big.py" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("baseline drift", out)

    def test_reduction_without_lowering_baseline_fails(self) -> None:
        """A genuine shrink must lower the pinned count in the same commit — it cannot just pass."""
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=180,
                baseline_toml='\n[line_cap_baseline]\n"src/big.py" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("baseline drift", out)

    def test_reduction_below_cap_requires_removing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=140,
                baseline_toml='\n[line_cap_baseline]\n"src/big.py" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("stale baseline entry", out)

    def test_reduction_below_cap_with_entry_removed_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(Path(directory), big_lines=140)
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 0)
            self.assertIn("0 baselined", out)

    def test_missing_file_baseline_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=140,
                baseline_toml='\n[line_cap_baseline]\n"src/gone.py" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("not in the scanned set", out)

    def test_directory_wide_baseline_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=200,
                baseline_toml='\n[line_cap_baseline]\n"src/*" = 200\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("not in the scanned set", out)
            self.assertIn("new unlisted violation", out)

    def test_non_integer_baseline_value_is_a_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = _write_repo(
                Path(directory), big_lines=200,
                baseline_toml='\n[line_cap_baseline]\n"src/big.py" = "200"\n',
            )
            code, out = captured_main(check_line_cap.main, ["--repo", directory, "--config", str(config)])
            self.assertEqual(code, 1)
            self.assertIn("must be an integer", out)

    def test_default_paths_scan_configured_source_and_common_dirs(self) -> None:
        """No explicit paths on the CLI: the configured source_dirs (and common) are scanned."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "common").mkdir()
            (root / "src" / "ok.py").write_text("x = 1\n", encoding="utf-8")
            (root / "common" / "ok.py").write_text("y = 2\n", encoding="utf-8")
            config = root / "quality.toml"
            config.write_text(
                'line_limit = 150\nline_mode = "logical"\nsource_dirs = ["src", "common"]\n'
                'test_dirs = []\nscript_dirs = []\ncode_extensions = [".py"]\nexclude_dirs = []\n',
                encoding="utf-8",
            )
            code, out = captured_main(check_line_cap.main, ["--repo", str(root), "--config", str(config)])
            self.assertEqual(code, 0)
            self.assertIn("2 file(s)", out)


if __name__ == "__main__":
    unittest.main()
