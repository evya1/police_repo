"""Tk presentation for an already verified league-kit replay."""

from __future__ import annotations

import tkinter as tk

from police_peer.replay_gui import ReplayData

_BG, _PANEL, _TEXT, _MUTED = "#0f172a", "#172033", "#e2e8f0", "#94a3b8"


def _moves(records: list[dict]) -> list[dict]:
    return [record for record in records if record.get("payload", {}).get("position")]


class ReplayWindow:
    """Small read-only replay UI with verified step navigation."""

    def __init__(self, data: ReplayData, report: str) -> None:
        self.data, self.report, self.index = data, report, 0
        self.own, self.opponent = _moves(data.own_records), _moves(data.opponent_records)
        self.root = tk.Tk()
        self.root.title(f"{data.role.upper()} REPLAY — {data.game_id}")
        self.root.configure(bg=_BG)
        self.root.geometry("970x690+10+10")
        self.canvas = tk.Canvas(self.root, width=560, height=560, bg=_BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, rowspan=2, padx=18, pady=18)
        self._build_header()
        self._build_panel()
        self._render()

    def _build_header(self) -> None:
        title = tk.Label(
            self.root, text="VERIFIED REPLAY", bg="#166534", fg="white",
            font=("Sans", 18, "bold"), padx=12, pady=10,
        )
        title.grid(row=0, column=0, columnspan=2, sticky="ew")

    def _build_panel(self) -> None:
        panel = tk.Frame(self.root, bg=_PANEL, padx=18, pady=18)
        panel.grid(row=1, column=1, sticky="nsew", padx=(0, 18), pady=18)
        self.step = self._label(panel, "Step", 0)
        self.integrity = self._label(panel, "Integrity", 2, "#86efac")
        self.audit = self._label(panel, "Mutual audit", 4, "#86efac")
        self.commitment = self._label(panel, "Commitment", 6)
        self.move = self._label(panel, "Recorded move", 8)
        self.hint = self._label(panel, "Natural-language hint", 10)
        self.outcome = self._label(panel, "Series outcome", 12)
        controls = tk.Frame(self.root, bg=_BG)
        controls.grid(row=2, column=1, sticky="nw", padx=(0, 18), pady=(0, 18))
        tk.Button(controls, text="◀ Previous", command=self._previous).pack(side="left")
        tk.Button(controls, text="Next ▶", command=self._next).pack(side="left", padx=8)

    @staticmethod
    def _label(parent: tk.Widget, caption: str, row: int, color: str = _TEXT) -> tk.Label:
        tk.Label(parent, text=caption.upper(), bg=_PANEL, fg=_MUTED,
                 font=("Sans", 9, "bold")).grid(row=row, column=0, sticky="w")
        value = tk.Label(parent, text="—", bg=_PANEL, fg=color, font=("Sans", 11),
                         justify="left", wraplength=330)
        value.grid(row=row + 1, column=0, sticky="w", pady=(1, 12))
        return value

    def _record(self, records: list[dict]) -> dict:
        return records[min(self.index, len(records) - 1)] if records else {"payload": {}}

    def _draw_board(self, own: dict, opponent: dict) -> None:
        self.canvas.delete("all")
        size, cell = self.data.board_size, 560 / self.data.board_size
        smell = own.get("payload", {}).get("smell_grid") or {}
        for row in range(size):
            for col in range(size):
                strength = min(1.0, max(0.0, float(smell.get(f"{row},{col}", 0.0))))
                red = int(30 + 150 * strength)
                green = int(40 + 50 * strength)
                blue = int(70 + 45 * (1 - strength))
                color = f"#{red:02x}{green:02x}{blue:02x}"
                self.canvas.create_rectangle(col * cell, row * cell, (col + 1) * cell,
                                             (row + 1) * cell, fill=color, outline="#475569")
        self._agent(own, cell, "P" if self.data.role == "police" else "T", "#38bdf8")
        other = "T" if self.data.role == "police" else "P"
        self._agent(opponent, cell, other, "#fb923c")

    def _agent(self, record: dict, cell: float, text: str, color: str) -> None:
        position = record.get("payload", {}).get("position")
        if not position:
            return
        row, col = position
        inset = 13
        self.canvas.create_oval(col * cell + inset, row * cell + inset,
                                (col + 1) * cell - inset, (row + 1) * cell - inset,
                                fill=color, outline="white", width=2)
        self.canvas.create_text((col + .5) * cell, (row + .5) * cell, text=text,
                                fill="#082f49", font=("Sans", 16, "bold"))

    def _render(self) -> None:
        own, opponent = self._record(self.own), self._record(self.opponent)
        payload = own.get("payload", {})
        total = max(len(self.own), len(self.opponent), 1)
        self.step.config(text=f"{self.index + 1} / {total}  •  {self.data.role.upper()}")
        self.integrity.config(text="Verified OK — both sealed halves")
        self.audit.config(text="PASSED" if self.data.audit_passed else "FAILED")
        self.commitment.config(text=f"{own.get('commit', '—')[:32]}…")
        self.move.config(text=f"{payload.get('move', '—')}  →  {payload.get('position', '—')}")
        self.hint.config(text=payload.get("hint") or "—")
        self.outcome.config(text=f"{self.data.result}  •  winner: {self.data.winner}")
        self._draw_board(own, opponent)

    def _next(self) -> None:
        self.index = min(self.index + 1, max(len(self.own), len(self.opponent)) - 1)
        self._render()

    def _previous(self) -> None:
        self.index = max(self.index - 1, 0)
        self._render()

    def run(self) -> None:
        self.root.mainloop()
