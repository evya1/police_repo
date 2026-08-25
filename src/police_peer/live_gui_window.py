"""Tk presentation of one peer's live local-truth event stream."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

_BG, _PANEL, _TEXT, _MUTED = "#0f172a", "#172033", "#e2e8f0", "#94a3b8"


class LiveWindow:
    """Read-only board plus a start control for the real peer runner."""

    def __init__(self, role: str, on_start: Callable[[], None], delay: float) -> None:
        self.role, self.on_start = role, on_start
        self.root = tk.Tk()
        self.root.title(f"{role.upper()} LIVE GUI — local truth")
        self.root.configure(bg=_BG)
        self.root.geometry("970x690+10+10")
        self.canvas = tk.Canvas(self.root, width=560, height=560, bg=_BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, rowspan=2, padx=18, pady=18)
        tk.Label(
            self.root, text="LIVE PEER — LOCAL TRUTH ONLY", bg="#075985", fg="white",
            font=("Sans", 18, "bold"), padx=12, pady=10,
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        self._build_panel(delay)
        self._empty_board(7)

    def _build_panel(self, delay: float) -> None:
        panel = tk.Frame(self.root, bg=_PANEL, padx=18, pady=18)
        panel.grid(row=1, column=1, sticky="nsew", padx=(0, 18), pady=18)
        self.phase = self._label(panel, "Status", 0, "#86efac")
        self.step = self._label(panel, "Sub-game / step", 2)
        self.position = self._label(panel, "My verified position", 4)
        self.move = self._label(panel, "My sealed move", 6)
        self.hint_in = self._label(panel, "Opponent says", 8)
        self.hint_out = self._label(panel, "My response", 10)
        self.barriers = self._label(panel, "Public barriers", 12)
        self.score = self._label(panel, "Audited sub-game score", 14)
        controls = tk.Frame(self.root, bg=_BG)
        controls.grid(row=2, column=1, sticky="nw", padx=(0, 18), pady=(0, 18))
        self.delay = tk.DoubleVar(value=delay)
        self.scale = tk.Scale(
            controls, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
            label="Display pacing (seconds)", variable=self.delay, length=210,
        )
        self.scale.pack()
        self.start = tk.Button(controls, text="Start live peer", command=self._start)
        self.start.pack(anchor="w", pady=6)

    @staticmethod
    def _label(parent: tk.Widget, caption: str, row: int, color: str = _TEXT) -> tk.Label:
        tk.Label(parent, text=caption.upper(), bg=_PANEL, fg=_MUTED,
                 font=("Sans", 9, "bold")).grid(row=row, column=0, sticky="w")
        value = tk.Label(parent, text="—", bg=_PANEL, fg=color, font=("Sans", 11),
                         justify="left", wraplength=330)
        value.grid(row=row + 1, column=0, sticky="w", pady=(1, 12))
        return value

    def _start(self) -> None:
        self.start.config(state="disabled")
        self.scale.config(state="disabled")
        self.phase.config(text="CONNECTING TO OPPONENT")
        self.on_start()

    def _empty_board(self, size: int) -> None:
        self._draw_board([[0.0] * size for _ in range(size)], [], None)

    def _draw_board(self, belief: list[list[float]], barriers: list, position: list | None) -> None:
        self.canvas.delete("all")
        size, cell = len(belief), 560 / len(belief)
        peak = max((value for row in belief for value in row), default=0.0)
        for row in range(size):
            for col in range(size):
                level = belief[row][col] / peak if peak else 0.0
                color = f"#{int(25 + 150 * level):02x}{int(45 + 30 * level):02x}78"
                self.canvas.create_rectangle(col * cell, row * cell, (col + 1) * cell,
                                             (row + 1) * cell, fill=color, outline="#475569")
        for row, col in barriers:
            self.canvas.create_rectangle(col * cell + 8, row * cell + 8,
                                         (col + 1) * cell - 8, (row + 1) * cell - 8,
                                         fill="#111827", outline="#f8fafc")
        if position:
            row, col = position
            self.canvas.create_oval(col * cell + 13, row * cell + 13,
                                    (col + 1) * cell - 13, (row + 1) * cell - 13,
                                    fill="#38bdf8", outline="white", width=2)
            self.canvas.create_text((col + .5) * cell, (row + .5) * cell,
                                    text=self.role[0].upper(), fill="#082f49",
                                    font=("Sans", 16, "bold"))

    def render(self, event: dict) -> None:
        self.phase.config(text=event["phase"])
        self.step.config(text=f"{event['sub_game']} / {event['step']}  •  {event['role'].upper()}")
        self.position.config(text=str(event["position"]))
        self.move.config(text=event.get("move") or "—")
        self.hint_in.config(text=event.get("opponent_hint") or "—")
        self.hint_out.config(text=event.get("hint") or "—")
        self.barriers.config(text=str(len(event["barriers"])))
        self.score.config(text=event.get("score") or "pending")
        self._draw_board(event["belief"], event["barriers"], event["position"])
        self.root.update_idletasks()
