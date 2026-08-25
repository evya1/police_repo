from __future__ import annotations

from pathlib import Path

from usage_dashboard_data import DashboardError

START = "<!-- ai-usage:start -->"
END = "<!-- ai-usage:end -->"


def update_readme(path: str | Path, content: str) -> None:
    try:
        readme = Path(path)
        original = readme.read_text(encoding="utf-8")
        if original.count(START) != 1 or original.count(END) != 1:
            raise DashboardError("README usage markers are missing or ambiguous")
        before, remainder = original.split(START, 1)
        _, after = remainder.split(END, 1)
        readme.write_text(before + START + "\n" + content + END + after, encoding="utf-8")
    except OSError:
        raise DashboardError("unable to update README") from None
