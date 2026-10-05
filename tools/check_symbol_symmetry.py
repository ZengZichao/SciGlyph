#!/usr/bin/env python3
"""校验安全标志类图标的 n 重旋转对称（ISO 361 / 生物危害标志的公开几何口径）。

辐射三叶（ISO 361）与生物危害标志都必须是绕画布中心严格 120° 三重对称：
把图标里所有几何锚点绕中心旋转 120°，若得到的点集与原图点集重合（允许 --tol 容差），
则该图标是三重对称的。旧版两枚标志的三叶方位角实测为 90°/180°/0°（间隔 90°、90°、180°），
本工具会把这种形判 FAIL，因此可以当作回归闸门。

用法：
  python3 tools/check_symbol_symmetry.py                    # 检查默认清单
  python3 tools/check_symbol_symmetry.py --order 3 --tol 0.25
  python3 tools/check_symbol_symmetry.py assets/09-safety-signage/... ...
"""
from __future__ import annotations

import argparse
import cmath
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = "{http://www.w3.org/2000/svg}"
NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
DEFAULT_TARGETS = sorted(
    str(p.relative_to(ROOT))
    for pat in ("*signal-biohazard.svg", "*signal-radiation-trefoil.svg",
                "hazard-signs/*hazard-biohazard.svg",
                "hazard-signs/*hazard-radioactive.svg")
    for p in (ROOT / "assets/09-safety-signage").rglob(pat)
    if "bin" not in p.stem and "bag" not in p.stem and "suit" not in p.stem
)


def path_points(d: str):
    """按命令逐段取路径坐标点（弧线 A/a 只取终点，跳过半径与标志位；相对命令累加）。"""
    pts = []
    cur, start = 0j, 0j
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|" + NUM, d)
    need = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
    cmd = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                cur = start
                pts.append((cur.real, cur.imag))
            continue
        per = need.get(cmd.upper())
        if per is None or i + per > len(tokens):
            break
        vals = [float(x) for x in tokens[i:i + per]]
        i += per
        rel = cmd.islower()
        dx, dy = (cur.real, cur.imag) if rel else (0.0, 0.0)
        cu = cmd.upper()
        if cu == "H":
            cur = complex(vals[0] + dx, cur.imag)
        elif cu == "V":
            cur = complex(cur.real, vals[0] + dy)
        else:
            cur = complex(vals[-2] + dx, vals[-1] + dy)
        if cu == "M":
            start = cur
        pts.append((round(cur.real, 4), round(cur.imag, 4)))
    return pts


def anchors(path: Path):
    tree = ET.parse(path).getroot()
    vb = [float(v) for v in tree.get("viewBox", "0 0 24 24").replace(",", " ").split()]
    cx, cy = (vb[0] + vb[2] / 2), (vb[1] + vb[3] / 2)
    pts = []
    for el in tree.iter():
        tag = el.tag.replace(SVG, "")
        if tag == "circle":
            pts.append((float(el.get("cx")), float(el.get("cy"))))
        elif tag == "ellipse":
            pts.append((float(el.get("cx")), float(el.get("cy"))))
        elif tag in ("line", "polyline", "polygon", "rect"):
            raw = " ".join(filter(None, (el.get("x1"), el.get("y1"), el.get("x2"), el.get("y2"),
                                         el.get("points"), el.get("x"), el.get("y"))))
            nums = [float(v) for v in re.findall(NUM, raw)]
            pts += list(zip(nums[0::2], nums[1::2]))
        elif tag == "path":
            pts += path_points(el.get("d", ""))
    # 中心点（同心圆、中心盘）不参与对称性判定，只判"外圈图元"
    outer = [(x, y) for x, y in pts if math.hypot(x - cx, y - cy) > 1e-6]
    return (cx, cy), outer


def rotate(pt, center, deg):
    cx, cy = center
    z = complex(pt[0] - cx, pt[1] - cy) * cmath.exp(1j * math.radians(deg))
    return (round(z.real + cx, 3), round(z.imag + cy, 3))


def check(path: Path, order: int, tol: float):
    center, outer = anchors(path)
    if not outer:
        return None, "无外圈图元"
    step = 360.0 / order
    bad = []
    for k in range(1, order):
        want = [rotate(p, center, step * k) for p in outer]
        pool = list(outer)
        for a in want:
            best, bi = None, -1
            for i, b in enumerate(pool):
                d = math.hypot(a[0] - b[0], a[1] - b[1])
                if best is None or d < best:
                    best, bi = d, i
            if best is None or best > tol:
                bad.append((round(step * k), a, None if best is None else pool[bi]))
                if best is not None:
                    pool.pop(bi)
        if len(bad) >= 40:
            break
    if bad:
        return False, (f"{order} 重旋转对称不成立：{len(bad)} 个锚点找不到对应，"
                       f"示例 {bad[0]}")
    return True, f"{order} 重旋转对称成立（tol={tol}）"


def main(argv=None):
    ap = argparse.ArgumentParser(description="安全标志 n 重旋转对称校验")
    ap.add_argument("files", nargs="*", help="待检查的 SVG（默认为两枚安全标志）")
    ap.add_argument("--order", type=int, default=3, help="旋转对称重数（默认 3）")
    ap.add_argument("--tol", type=float, default=0.25, help="锚点坐标容差（viewBox 单位）")
    args = ap.parse_args(argv)

    rels = args.files or DEFAULT_TARGETS
    fail = 0
    for rel in rels:
        p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not p.exists():
            print(f"FAIL {rel}: 文件不存在")
            fail += 1
            continue
        ok, msg = check(p, args.order, args.tol)
        show = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
        if ok is None:
            print(f"SKIP {show}: {msg}")
            continue
        fail += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {show}: {msg}")
    print(f"合计 {len(rels)} 项，失败 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
