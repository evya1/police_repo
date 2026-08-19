from pathlib import Path

from police_peer.reporting.schemas import SCHEMA_VERSION


def test_internal_contract_label():
    assert SCHEMA_VERSION.startswith("internal-")

    readme_path = Path("config/official/reporting/README.md")
    assert readme_path.exists()

    content = readme_path.read_text()
    assert "INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE" in content

    # Ensure no fixture is marked "official"
    fixtures_path = Path("tests/contract/report_schemas/fixtures")
    if fixtures_path.exists():
        for f in fixtures_path.iterdir():
            if f.is_file():
                content = f.read_text()
                assert "official" not in content.lower()
