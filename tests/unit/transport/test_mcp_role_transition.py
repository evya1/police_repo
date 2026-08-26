from common.domain.scoring import Role
from common.transport.mcp_client import McpChannel


def _channel(start_url: str, *, failures: int = 0) -> tuple[McpChannel, list[float]]:
    channel = McpChannel.__new__(McpChannel)
    channel.peer_url = start_url
    channel.timeout = 30.0
    channel._opponent_urls = {
        "police": "https://opponent-police.example/mcp",
        "thief": "https://opponent-thief.example/mcp",
    }
    channel._teardown = lambda: None
    attempts: list[float] = []

    def connect(*, timeout: float | None = None) -> None:
        attempts.append(float(timeout or 0.0))
        if len(attempts) <= failures:
            raise TimeoutError("transient boundary failure")

    channel._connect = connect
    return channel, attempts


def test_role_transition_retries_and_selects_opponent_thief(monkeypatch) -> None:
    channel, attempts = _channel("https://opponent-police.example/mcp", failures=2)
    monkeypatch.setattr("common.transport.mcp_client.time.sleep", lambda _delay: None)

    channel.select_for_role(Role.POLICE)

    assert channel.peer_url == "https://opponent-thief.example/mcp"
    assert len(attempts) == 3
    assert all(0 < timeout <= 10 for timeout in attempts)


def test_thief_selects_opponent_police() -> None:
    channel, attempts = _channel("https://opponent-thief.example/mcp")

    channel.select_for_role(Role.THIEF)

    assert channel.peer_url == "https://opponent-police.example/mcp"
    assert len(attempts) == 1
