from common.domain.scoring import Role
from common.transport.mcp_session import McpSession


def _session(start_url: str, *, failures: int = 0) -> tuple[McpSession, list[float]]:
    session = McpSession.__new__(McpSession)
    session.peer_url = start_url
    session.timeout = 30.0
    session.transition_timeout = 30.0
    session.opponent_urls = {
        "police": "https://opponent-police.example/mcp",
        "thief": "https://opponent-thief.example/mcp",
    }
    session.teardown = lambda: None
    attempts: list[float] = []

    def connect(*, timeout: float | None = None) -> None:
        attempts.append(float(timeout or 0.0))
        if len(attempts) <= failures:
            raise TimeoutError("transient boundary failure")

    session.connect = connect
    return session, attempts


def test_role_transition_retries_and_selects_opponent_thief(monkeypatch) -> None:
    session, attempts = _session("https://opponent-police.example/mcp", failures=2)
    monkeypatch.setattr("common.transport.mcp_session.time.sleep", lambda _delay: None)

    session.select_for_role(Role.POLICE)

    assert session.peer_url == "https://opponent-thief.example/mcp"
    assert len(attempts) == 3
    assert all(0 < timeout <= 10 for timeout in attempts)


def test_thief_selects_opponent_police() -> None:
    session, attempts = _session("https://opponent-thief.example/mcp")

    session.select_for_role(Role.THIEF)

    assert session.peer_url == "https://opponent-police.example/mcp"
    assert len(attempts) == 1
