"""Lifecycle adapter between the Tk Live GUI and the production peer runner."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from police_peer.live_gui_window import LiveWindow


class LiveGuiApp:
    """Run the peer off the Tk thread and render its read-only local events."""

    def __init__(
        self, runner: Callable[..., int], *, auto_start: bool = False, step_delay: float = 0.15,
    ) -> None:
        self.runner, self.events = runner, queue.Queue()
        self.delay, self.exit_code, self.started = step_delay, 0, False
        self.window = LiveWindow("police", self.start, step_delay)
        self.window.root.after(80, self._poll)
        if auto_start:
            self.window.root.after(250, self.window._start)

    def start(self) -> None:
        if self.started:
            return
        self.started = True
        self.delay = float(self.window.delay.get())
        threading.Thread(target=self._worker, daemon=True).start()

    def _listener(self, event: dict) -> None:
        self.events.put(event)

    def _worker(self) -> None:
        code = self.runner(listener=self._listener)
        self.events.put({"runner_exit": code})

    def _poll(self) -> None:
        if not self.events.empty():
            event = self.events.get_nowait()
            if "runner_exit" in event:
                self.exit_code = int(event["runner_exit"])
                self.window.phase.config(text=f"PEER EXITED — CODE {self.exit_code}")
            else:
                self.window.render(event)
        self.window.root.after(max(50, int(self.delay * 1000)), self._poll)

    def run(self) -> int:
        self.window.root.mainloop()
        return self.exit_code


def launch_live_gui(
    runner: Callable[..., int], *, auto_start: bool = False, step_delay: float = 0.15,
) -> int:
    """Open the actual local-truth GUI around one independently running peer."""
    return LiveGuiApp(runner, auto_start=auto_start, step_delay=step_delay).run()
