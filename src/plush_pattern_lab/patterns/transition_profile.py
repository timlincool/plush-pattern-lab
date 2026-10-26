"""Bounded purely geometric taper for local cap-to-gore reference separation."""

from __future__ import annotations


def cap_offset_weight(row: int, total_rows: int, transition_rows: int) -> float:
    """1 in the panel body; approach 0 only at cap ring if rows > 0.

    A change to *initial simulated geometry*, never a physical material model.
    The default zero-transition reproduces existing experiments bit-for-bit.
    """
    if any(type(value) is not int for value in (row, total_rows, transition_rows)):
        raise ValueError("Transition indices must be integers")
    if total_rows < 25 or not 0 <= row < total_rows:
        raise ValueError("Invalid panel mesh row")
    if not 0 <= transition_rows <= 8 or 2 * transition_rows >= total_rows:
        raise ValueError("Transition exceeds bounded cap-join region")
    if transition_rows == 0:
        return 1.0
    return float(
        min(1.0, row / transition_rows, (total_rows - 1 - row) / transition_rows)
    )
