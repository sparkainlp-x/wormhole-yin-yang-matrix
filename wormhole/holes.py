"""Black-hole and white-hole cells on the wormhole.

The names are an analogy for one-way crossing rules in this classical
toy. NOTHING astrophysical is modelled: no event horizon, no
singularity, no spacetime curvature, no Hawking radiation, no
information paradox. The rules affect ONLY wormhole crossings; each
engine's own step is untouched, and the receiving engine's frozen
guards still decide every crossing (a masked candidate can still be
refused, and a refused crossing still commits nothing).

- A BLACK cell is a sink: nothing leaves it through the wormhole.
  In a crossing FROM its engine, that cell's contribution is zeroed:
  the destination keeps its own cell there. The cell still RECEIVES
  normally (subject to frozen guards): a sink absorbs.
- A WHITE cell is a source: nothing enters it through the wormhole.
  In a crossing INTO its engine, that cell's contribution is zeroed:
  the destination keeps its own cell there. The cell still EMITS
  normally: a source only gives.
- A cell cannot be both black and white. Cells outside the 3x3 grid
  are rejected. No holes (the default) reproduces v0.3.0 exactly:
  the same seeds give the same crossings, pinned by test.
"""

from __future__ import annotations

import numpy as np

GRID = 3


class HoleMap:
    """Per-engine hole designation, frozen at pair construction.

    ``black`` and ``white`` are iterables of (row, col) cells on the
    3x3 grid. Empty by default (no holes, v0.3.0 behavior).
    """

    def __init__(self, black=(), white=()):
        black = {tuple(cell) for cell in black}
        white = {tuple(cell) for cell in white}
        for cell in black | white:
            if (len(cell) != 2
                    or not all(isinstance(x, int) and not isinstance(x, bool)
                               for x in cell)
                    or not (0 <= cell[0] < GRID and 0 <= cell[1] < GRID)):
                raise ValueError(
                    f"hole cell must be (row, col) on the 3x3 grid, got {cell!r}")
        clash = black & white
        if clash:
            raise ValueError(
                f"cell cannot be both black and white: {sorted(clash)}")
        self.black = frozenset(black)
        self.white = frozenset(white)

    def source_mask(self):
        """(3, 3) bool array: True where a source cell is black.

        Used on the SOURCE side of a crossing: masked cells do not
        leave their engine.
        """
        mask = np.zeros((GRID, GRID), dtype=bool)
        for row, col in self.black:
            mask[row, col] = True
        return mask

    def dest_mask(self):
        """(3, 3) bool array: True where a dest cell is white.

        Used on the DESTINATION side of a crossing: masked cells do
        not accept incoming contributions.
        """
        mask = np.zeros((GRID, GRID), dtype=bool)
        for row, col in self.white:
            mask[row, col] = True
        return mask

    def cells(self):
        """Sorted hole cells, for summaries and reports."""
        return {"black": sorted(self.black), "white": sorted(self.white)}

    def __bool__(self):
        return bool(self.black or self.white)
