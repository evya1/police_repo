"""The private TOML's App. B section 4 sections, and the precedence that protects the contract."""

from __future__ import annotations

import textwrap

from common.transport.terms import project_terms
from police_peer.wire.config import build_peer_config, load_private
from police_peer.wire.identity_config import LECTURER_REPORT_ADDRESS


def write(tmp_path, body: str):
    path = tmp_path / "game.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_an_absent_file_yields_safe_defaults(tmp_path):
    private = load_private(tmp_path / "missing.toml")
    assert private.identity.group_name == ""
    assert private.email.recipient == LECTURER_REPORT_ADDRESS
    assert LECTURER_REPORT_ADDRESS == "rmisegal+uoh26finalgame@gmail.com"
    assert private.email.mode == "dry-run"


def test_every_appendix_b_section_parses(tmp_path):
    path = write(tmp_path, """
        min_center_intensity = 0.5
        [game]
        group_name = "ZeroOne"
        group_id = "zeroone"
        members = ["id-1001", "id-1002"]
        repos = { cop = "https://example.invalid/p", thief = "https://example.invalid/t" }
        [network]
        my_port = 8101
        opponent_url = "http://127.0.0.1:8102/mcp"
        turn_timeout_seconds = 180
        [llm]
        model = "template"
        step_deadline_seconds = 30
        [email]
        recipient = "someone@example.invalid"
        mode = "send"
    """)
    private = load_private(path)
    assert private.identity.group_name == "ZeroOne"
    assert private.identity.members == ("id-1001", "id-1002")
    assert private.identity.repos["cop"].endswith("/p")
    assert private.endpoints.my_port == 8101
    assert private.endpoints.opponent_url.endswith("/mcp")
    assert private.llm.model == "template"
    assert private.email.recipient == "someone@example.invalid"
    assert private.email.mode == "send"


def test_the_group_id_may_be_declared_in_the_game_section(tmp_path):
    path = write(tmp_path, """
        [game]
        group_id = "zeroone"
    """)
    assert load_private(path).group_id == "zeroone"


def test_sending_is_opt_in_by_default(tmp_path):
    path = write(tmp_path, """
        [email]
        recipient = "someone@example.invalid"
    """)
    assert load_private(path).email.mode == "dry-run"


def test_the_shipped_example_parses(tmp_path):
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / ".." / "config" / "game.toml.example"
    private = load_private(example.resolve())
    assert private.email.recipient == LECTURER_REPORT_ADDRESS


def test_the_signed_json_beats_the_private_toml_on_a_shared_key(tmp_path):
    """The private file may add local settings; it may never weaken a signed condition."""
    from pathlib import Path

    shared = Path(__file__).resolve().parents[2] / "config" / "game.json"
    path = write(tmp_path, """
        [board_and_agents]
        grid_size = 3
    """)
    terms = build_peer_config(shared, load_private(path))
    assert terms["board_size"] == 7, "the shared contract wins"
    assert terms["num_games"] == 6


def test_min_center_intensity_is_the_one_wire_relevant_private_value(tmp_path):
    path = write(tmp_path, "min_center_intensity = 0.7\n")
    private = load_private(path)
    terms = project_terms({}, private.__dict__)
    assert terms["min_center_intensity"] == 0.7
