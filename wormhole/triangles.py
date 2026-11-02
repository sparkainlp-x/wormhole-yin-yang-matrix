"""Triangle hole patterns: three hole cells forming a triangle.

TRIANGLE_CELLS is the three corners (0, 0), (0, 2), (2, 0): a right
isosceles triangle (legs 2 and 2, hypotenuse 2*sqrt(2), area 2).
The choice among corner triples is immaterial up to square
symmetry: the D4 symmetries of the square map any three corners to
any other three, so one corner triangle stands for all of them.

It is NOT equilateral, and no 3-cell triangle on this grid can be:
no equilateral triangle has all three vertices on integer lattice
points (its area would be irrational, against Pick's theorem).
The Tesla 3-6-9 triangle is equilateral on the 9-gon of digits, a
different diagram; here the triangle is a pattern of hole cells
on the 3x3 membrane grid, and its geometry is stated exactly.

A triangle pattern plugs straight into the v0.4.0 HoleMap: use it
black on one engine, white on the other, or black on both (both
crossing directions masked). The structural fact to remember:
black-on-yin and white-on-yang mask the SAME candidate cells in
the yin->yang direction and leave the yang->yin direction
unmasked, so those two conditions run IDENTICALLY (pinned by
test), exactly as the single-cell (1, 1) pair did in v0.4.0.
"""

from __future__ import annotations

from .holes import HoleMap

TRIANGLE_CELLS = ((0, 0), (0, 2), (2, 0))


def triangle_area2(cells=TRIANGLE_CELLS):
    """Twice the triangle's area, by determinant (exact integer)."""
    (x1, y1), (x2, y2), (x3, y3) = cells
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))


def is_triangle(cells):
    """True when cells are 3 distinct in-grid cells, non-collinear."""
    cells = [tuple(c) for c in cells]
    if len(cells) != 3 or len(set(cells)) != 3:
        return False
    if not all(len(c) == 2 and 0 <= c[0] < 3 and 0 <= c[1] < 3
               for c in cells):
        return False
    return triangle_area2(cells) > 0


def triangle_black(cells=TRIANGLE_CELLS):
    """HoleMap with the triangle cells black (sinks)."""
    if not is_triangle(cells):
        raise ValueError(f"not a triangle of 3 grid cells: {cells!r}")
    return HoleMap(black=cells)


def triangle_white(cells=TRIANGLE_CELLS):
    """HoleMap with the triangle cells white (sources)."""
    if not is_triangle(cells):
        raise ValueError(f"not a triangle of 3 grid cells: {cells!r}")
    return HoleMap(white=cells)
