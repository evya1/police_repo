"""Tests for configuration, document, and line-cap checks."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_docs_present  # noqa: E402
import check_line_cap  # noqa: E402
import quality_common  # noqa: E402


class LineAndDocumentTests(unittest.TestCase):
    """Exercise line counting, configuration, and document validation."""

    def test_raw_and_logical_line_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "module.py"
            source.write_text("# explanation\n\nvalue = 1\n", encoding="utf-8")
            self.assertEqual(check_line_cap.raw_line_count(source), 3)
            self.assertEqual(check_line_cap.logical_line_count(source), 1)

    def test_logical_count_for_non_python_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "module.js"
            source.write_text("// note\n\nconst value = 1;\n", encoding="utf-8")
            self.assertEqual(check_line_cap.logical_line_count(source), 1)

    def test_collect_files_skips_excluded_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            cache = source / "__pycache__"
            cache.mkdir(parents=True)
            (source / "kept.py").write_text("x = 1\n", encoding="utf-8")
            (cache / "ignored.py").write_text("x = 1\n", encoding="utf-8")
            files = check_line_cap.collect_files(
                root, [Path("src")], {".py"}, {"__pycache__"}
            )
            self.assertEqual(files, [source / "kept.py"])

    def test_collect_files_rejects_missing_path(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(quality_common.QualityError, "not found"),
        ):
            check_line_cap.collect_files(
                Path(directory), [Path("missing")], {".py"}, set()
            )

    def test_find_line_cap_violations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "module.py"
            source.write_text("x = 1\ny = 2\n", encoding="utf-8")
            self.assertEqual(
                check_line_cap.find_violations([source], 1, "logical"), [(source, 2)]
            )

    def test_line_cap_main_reads_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/app.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            config = root / "quality.toml"
            config.write_text(
                """line_limit = 1
line_mode = "logical"
source_dirs = ["src"]
test_dirs = []
script_dirs = []
code_extensions = [".py"]
exclude_dirs = []
""",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = check_line_cap.main(
                    ["--repo", str(root), "--config", str(config)]
                )
            self.assertEqual(result, 1)
            self.assertIn("exceed", output.getvalue())

    def test_missing_documents_reports_only_absent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("ready\n", encoding="utf-8")
            missing = check_docs_present.missing_documents(
                root, ["README.md", "docs/PRD.md"]
            )
            self.assertEqual(missing, ["docs/PRD.md"])

    def test_configuration_type_validation(self) -> None:
        with self.assertRaisesRegex(quality_common.QualityError, "list of strings"):
            quality_common.string_list({"paths": "src"}, "paths")
        with self.assertRaisesRegex(quality_common.QualityError, "positive integer"):
            quality_common.integer_value({"limit": 0}, "limit")


if __name__ == "__main__":
    unittest.main()
