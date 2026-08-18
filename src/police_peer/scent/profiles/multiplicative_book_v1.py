"""Multiplicative book scent profile (book-oriented alternative).

Implements M-01 §B.2, the book-oriented profile, from the official game book
(Book v3.0.0, ch. 4). Kernel values, evaluation order, and clamp policy are pinned by
``vectors/scent_book_v3.json`` — do not refit them to a closed form.

M-01 §B.2: verbatim 5x5 figure-4 kernel lookup, multiplicative decay,
decay-then-deposit, no rounding, [0, 0.9] clamp, recomputed rather than transmitted.
"""

# Book v3.0.0 figure 4 — printed values, verbatim lookup. Not a closed form on purpose:
# two teams fitting their own Gaussian land in disjoint sigma windows and get different
# fields. The printed 25 values are the only thing both implementations can both reach.
BOOK_KERNEL = (
    (0.04, 0.14, 0.20, 0.14, 0.04),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.20, 0.62, 0.90, 0.62, 0.20),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.04, 0.14, 0.20, 0.14, 0.04),
)


def book_kernel_delta(dr: int, dc: int) -> float:
    """The deposit at offset (dr, dc) from the emitting agent — a VERBATIM table lookup.

    Not a closed form on purpose. The printed values are reproducible by a radial Gaussian,
    but only inside a narrow sigma window that the book never prints, and the window differs
    by quantization rule (see closed_form_probe in vectors/scent_book_v3.json). Two teams
    each fitting their own Gaussian get different fields; the printed table is the only thing
    both can land on.
    """
    if abs(dr) > 2 or abs(dc) > 2:
        return 0.0
    return BOOK_KERNEL[dr + 2][dc + 2]


def book_update(tau: float, delta: float, rho: float, center_intensity: float) -> float:
    """One cell, one full turn: tau' = clamp((1 - rho) * tau + delta, 0, center_intensity).

    Evaluation order is load-bearing and pinned exactly as written. The model does NO
    rounding, so the algebraically-equivalent `tau - rho * tau + delta` differs from this in
    the last bit for many inputs (75 of 534 probed) — enough to break a byte-comparison of two
    recomputed fields. Compute it in this order, or compare fields with a tolerance.

    The upper clamp is NOT in the book's printed formula, which shows only `max(0, ...)`; it
    comes from the book's own declaration that tau is a continuous value in [0, 0.9]. Without
    it a cell that decays and is re-deposited on exceeds the centre intensity (the 1.43 case).
    """
    return min(max(0.0, (1 - rho) * tau + delta), center_intensity)


def book_full_turn(field: dict[str, float], center: tuple[int, int], rho: float,
                   center_intensity: float, board_size: int) -> dict[str, float]:
    """One FULL turn of one agent's own trail: decay everything, deposit the kernel, clamp.

    Cadence is the book's: the update runs once per full turn, after both agents have moved —
    not once per half-turn step. Decay and deposit are a single expression, so decay applies
    to the pre-existing field only (decay-then-deposit). The reference model does the reverse
    (deposit, then decay before sending), which is one of the two models' real divergences.

    Each side recomputes the rival's field from revealed actions; nothing is received, so
    there is no receiver-side decay pass.
    """
    cells = set(field) | {
        f"{center[0] + dr},{center[1] + dc}"
        for dr in range(-2, 3) for dc in range(-2, 3)
        if 0 <= center[0] + dr < board_size and 0 <= center[1] + dc < board_size
    }
    out: dict[str, float] = {}
    # Sorted by (row, col): set iteration order varies between runs, and while key order cannot
    # change a hash (canonicalization sorts), it would make the committed fixture drift in CI.
    for key in sorted(cells, key=lambda k: tuple(int(x) for x in k.split(","))):
        r, c = (int(x) for x in key.split(","))
        value = book_update(
            field.get(key, 0.0),
            book_kernel_delta(r - center[0], c - center[1]),
            rho,
            center_intensity,
        )
        if value > 0.0:
            out[key] = value
    return out
