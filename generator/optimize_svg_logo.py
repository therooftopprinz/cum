#!/usr/bin/env python3
"""
Shrink dense polygonal paths with Visvalingam–Whyatt (fewer vertices, still
compact relative `l` deltas). Existing cubic commands are kept as-is.

Why not “everything to curves”? For this logo, short `l dx dy` chains are
already extremely compact; emitting many `c` verbs usually *increases* file
size, so this tool targets vertex reduction + tighter encoding instead.

Requires: pip install svg.path

  python generator/optimize_svg_logo.py [--area A] [--corner DEG] input.svg output.svg
"""

from __future__ import annotations

import argparse
import cmath
import math
import re
import xml.etree.ElementTree as ET
from typing import List

from svg.path import Close, CubicBezier, Line, Move, Path, parse_path


def tri_area(a: complex, b: complex, c: complex) -> float:
    return abs((b.real - a.real) * (c.imag - a.imag) - (b.imag - a.imag) * (c.real - a.real))


def vw_simplify(pts: List[complex], area_thresh: float, closed: bool) -> List[complex]:
    pts = pts[:]
    if len(pts) < 3:
        return pts
    if not closed:
        while len(pts) > 2:
            best_i, best_a = -1, float("inf")
            for i in range(1, len(pts) - 1):
                ta = tri_area(pts[i - 1], pts[i], pts[i + 1])
                if ta < best_a:
                    best_a, best_i = ta, i
            if best_a > area_thresh:
                break
            pts.pop(best_i)
        return pts

    while len(pts) > 3:
        best_i, best_a = -1, float("inf")
        n = len(pts)
        for i in range(n):
            ta = tri_area(pts[(i - 1) % n], pts[i], pts[(i + 1) % n])
            if ta < best_a:
                best_a, best_i = ta, i
        if best_a > area_thresh:
            break
        pts.pop(best_i)
    return pts


def abs_turn_deg(a: complex, b: complex, c: complex) -> float:
    u, v = b - a, c - b
    if abs(u) < 1e-9 or abs(v) < 1e-9:
        return 0.0
    return abs(math.degrees(cmath.phase(v / u)))


def split_polyline_open(points: List[complex], corner_deg: float) -> List[List[complex]]:
    if len(points) < 3:
        return [points]
    seams = [0]
    for i in range(1, len(points) - 1):
        if abs_turn_deg(points[i - 1], points[i], points[i + 1]) > corner_deg:
            seams.append(i)
    seams.append(len(points) - 1)
    return [points[a : b + 1] for a, b in zip(seams, seams[1:])]


def split_polyline_closed_core(
    core: List[complex], corner_deg: float
) -> List[List[complex]]:
    n = len(core)
    if n < 3:
        return []
    corners = [
        i
        for i in range(n)
        if abs_turn_deg(core[(i - 1) % n], core[i], core[(i + 1) % n]) > corner_deg
    ]
    if len(corners) < 2:
        return [core + [core[0]]]

    chains: List[List[complex]] = []
    nc = len(corners)
    for k in range(nc):
        i0 = corners[k]
        i1 = corners[(k + 1) % nc]
        if i1 > i0:
            seg = [core[j] for j in range(i0, i1 + 1)]
        else:
            seg = [core[j] for j in range(i0, n)] + [core[j] for j in range(0, i1 + 1)]
        if abs(seg[0] - seg[-1]) > 1e-3:
            seg.append(seg[0])
        chains.append(seg)
    return chains


def partition(points: List[complex], closing: bool, corner_deg: float):
    if closing and len(points) > 3 and abs(points[0] - points[-1]) < 1e-3:
        core = points[:-1]
        if len(core) < 3:
            return [[points]]
        return split_polyline_closed_core(core, corner_deg)
    return split_polyline_open(points, corner_deg)


def rnd(z: complex) -> complex:
    return complex(int(round(z.real)), int(round(z.imag)))


def chain_to_line_pairs(
    ch: List[complex], closed_ring: bool, area_thresh: float
) -> List[tuple[complex, complex]]:
    """Absolute start/end segments after simplification."""
    if len(ch) < 2:
        return []
    dup = closed_ring or abs(ch[0] - ch[-1]) < 1e-3
    verts = ch[:-1] if dup and len(ch) > 2 else ch[:]
    if len(verts) < 2:
        return []
    simp = vw_simplify(verts, area_thresh, closed=closed_ring)
    pairs: List[tuple[complex, complex]] = [
        (rnd(simp[i]), rnd(simp[i + 1])) for i in range(len(simp) - 1)
    ]
    if closed_ring and len(simp) >= 3:
        pairs.append((rnd(simp[-1]), rnd(simp[0])))
    return pairs


def flush_lines(
    out: Path,
    line_buf: List[Line],
    move_start: complex,
    closing: bool,
    area_thresh: float,
    corner_deg: float,
):
    if not line_buf:
        return

    pts = [line_buf[0].start]
    for ln in line_buf:
        pts.append(ln.end)

    if closing and abs(pts[-1] - move_start) > 1e-3:
        pts.append(move_start)

    prev_abs = rnd(out[-1].end) if len(out) > 0 else rnd(line_buf[0].start)

    for ch in partition(pts, closing, corner_deg):
        closed_ring = len(ch) > 3 and abs(ch[0] - ch[-1]) < 1e-3
        for a, b in chain_to_line_pairs(ch, closed_ring, area_thresh):
            a, b = rnd(a), rnd(b)
            if a == b:
                continue
            if a != prev_abs:
                out.append(Line(prev_abs, a, relative=False))
            out.append(Line(a, b, relative=True))
            prev_abs = b

    if closing:
        out.append(Close(prev_abs, rnd(move_start)))


def optimize_path(path: Path, area_thresh: float, corner_deg: float) -> Path:
    out = Path()
    line_buf: List[Line] = []
    move_start = 0j

    for seg in path:
        if isinstance(seg, Move):
            if line_buf:
                flush_lines(
                    out, line_buf, move_start, False, area_thresh, corner_deg
                )
                line_buf = []
            out.append(seg)
            move_start = seg.start
        elif isinstance(seg, Line):
            line_buf.append(seg)
        elif isinstance(seg, CubicBezier):
            if line_buf:
                flush_lines(
                    out, line_buf, move_start, False, area_thresh, corner_deg
                )
                line_buf = []
            out.append(seg)
        elif isinstance(seg, Close):
            flush_lines(out, line_buf, move_start, True, area_thresh, corner_deg)
            line_buf = []
        else:
            raise TypeError(f"unsupported {type(seg)}")
    if line_buf:
        flush_lines(out, line_buf, move_start, False, area_thresh, corner_deg)
    return out


def shorten_d(raw: str) -> str:
    s = raw.replace(",", " ").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"([MmLlHhVvCcSsQqTtAaZz])\s+", r"\1", s)
    return s


def rgb_to_hex(s: str) -> str:
    inner = s[s.find("(") + 1 : s.rfind(")")]
    r, g, b = [int(float(x.strip())) for x in inner.split(",")[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"


def iter_path_ds(group: ET.Element) -> List[str]:
    out: List[str] = []
    stack = [group]
    while stack:
        el = stack.pop()
        for ch in el:
            tag = ch.tag.split("}")[-1]
            if tag == "path":
                d = ch.get("d")
                if d:
                    out.append(d)
            else:
                stack.append(ch)
    return out


def rewrite_svg(inp: bytes, area_thresh: float, corner_deg: float) -> str:
    root = ET.fromstring(inp)
    groups: List[str] = []
    vb = root.get("viewBox") or "0 0 10240 10240"
    for g in root:
        fill = g.get("fill", "")
        if fill.startswith("rgb"):
            ff = rgb_to_hex(fill)
        elif fill.startswith("#"):
            ff = fill
        else:
            ff = "#000000"
        parts_opt: List[str] = []
        for d in iter_path_ds(g):
            opt = optimize_path(parse_path(d), area_thresh, corner_deg)
            parts_opt.append(shorten_d(opt.d()))
        if parts_opt:
            mega = " ".join(parts_opt)
            groups.append(f'<g fill="{ff}"><path d="{mega}"/></g>')

    w, h = root.get("width", "512"), root.get("height", "512")

    svg = (
        "<svg xmlns=\"http://www.w3.org/2000/svg\""
        f' width="{w}" height="{h}" viewBox="{vb}">'
        + "".join(groups)
        + "</svg>"
    )
    ET.fromstring(svg.encode("utf-8"))
    return svg


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument(
        "--area",
        type=float,
        default=9000.0,
        help="VW triangle area threshold (coordinate^2). Larger = bolder.",
    )
    ap.add_argument(
        "--corner",
        type=float,
        default=40.0,
        help="Preserve corners sharper than this (degrees).",
    )
    ns = ap.parse_args()
    with open(ns.input, "rb") as f:
        data = f.read()
    out = rewrite_svg(data, ns.area, ns.corner)
    with open(ns.output, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {ns.output}: {len(out)} bytes")


if __name__ == "__main__":
    main()
