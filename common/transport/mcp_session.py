"""Stateful lifecycle for the synchronous facade over one async MCP session."""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections.abc import Callable


class PeerUnreachableError(Exception):
    """The opponent stayed unreachable after the one permitted reconnect."""


class McpSession:
    """Own an event loop, async client, reconnect policy, and role endpoints."""

    def __init__(
        self,
        peer_url: str,
        timeout: float,
        client_factory: Callable[[str], object],
    ) -> None:
        self.peer_url = peer_url
        self.timeout = timeout
        self.client_factory = client_factory
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(
            target=self.loop.run_forever, name="mcp-client-loop", daemon=True
        )
        self.loop_thread.start()
        self.client: object | None = None
        self.opponent_urls: dict[str, str] = {}
        self.transition_timeout = timeout
        try:
            self.connect()
        except Exception:  # noqa: BLE001 - never leak the loop thread on a failed open
            self.stop_loop()
            raise

    def submit(self, coroutine, timeout: float | None = None):
        """Drive a coroutine on the private loop and cancel it on failure."""
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        try:
            return future.result(timeout=timeout if timeout is not None else self.timeout)
        except Exception:
            future.cancel()
            raise

    def stop_loop(self) -> None:
        """Stop the private event loop and join its daemon thread. Idempotent."""
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join(timeout=5.0)

    def connect(self, *, timeout: float | None = None) -> None:
        """Open or reopen the held session to the current peer URL."""
        attempt_timeout = self.timeout if timeout is None else timeout
        client = self.client_factory(self.peer_url)
        try:
            self.submit(client.__aenter__(), timeout=attempt_timeout)
        except Exception:
            with contextlib.suppress(Exception):
                self.submit(client.__aexit__(None, None, None), timeout=5.0)
            raise
        self.client = client

    def teardown(self) -> None:
        """Close the current async client, if any."""
        if self.client is not None:
            with contextlib.suppress(Exception):
                self.submit(self.client.__aexit__(None, None, None), timeout=5.0)
            self.client = None

    def call_tool(
        self,
        tool: str,
        args: dict,
        *,
        transform: Callable[[object], object] | None = None,
    ) -> object:
        """Call once, reconnect once on transport failure, and preserve one deadline."""
        async def invoke() -> object:
            result = await self.client.call_tool(tool, args)
            return transform(result) if transform is not None else result

        deadline = time.monotonic() + self.timeout
        try:
            return self.submit(invoke(), timeout=self.timeout)
        except Exception:  # noqa: BLE001 - reconnect once inside the original deadline
            self.teardown()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PeerUnreachableError(
                    f"peer at {self.peer_url} timed out; no time to retry"
                ) from None
            try:
                time.sleep(min(0.5, max(0.0, remaining / 4)))
                self.connect()
                return self.submit(invoke(), timeout=max(0.1, deadline - time.monotonic()))
            except PeerUnreachableError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise PeerUnreachableError(
                    f"peer at {self.peer_url} unreachable after re-establish: {exc}"
                ) from exc

    def configure_endpoints(
        self, *, police_url: str, thief_url: str, transition_timeout: float | None = None
    ) -> None:
        """Install the opponent's role endpoints for the alternating series."""
        self.opponent_urls = {"police": police_url, "thief": thief_url}
        self.transition_timeout = transition_timeout or self.timeout

    def select_for_role(self, our_role) -> None:
        """Dial the complementary-role endpoint with bounded retries."""
        role = getattr(our_role, "value", str(our_role))
        opponent_role = "thief" if role == "police" else "police"
        target = self.opponent_urls.get(opponent_role)
        if not target or target == self.peer_url:
            return
        self.teardown()
        self.peer_url = target
        deadline = time.monotonic() + self.transition_timeout
        delay = 0.5
        last_error: Exception | None = None
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                self.connect(timeout=min(10.0, remaining))
                return
            except Exception as exc:  # noqa: BLE001 - retry transient boundary failures
                last_error = exc
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(delay, remaining))
                delay = min(5.0, delay * 2.0)
        raise PeerUnreachableError(
            f"peer at {self.peer_url} did not accept an MCP session during role transition: "
            f"{last_error}"
        ) from last_error

    def close(self) -> None:
        """Tear down the client and stop the private loop."""
        self.teardown()
        self.stop_loop()
