#!/usr/bin/env python3
"""标签零重叠检查 / 保守修复（新结构版，自包含，扫描 assets/）。

口径与 tools/svgtext.py 一致：累计仿射变换的近似字形盒 + 0.6 pad。
`--fix` 只把重叠对里的一枚标签沿 y 挪开——只挪位置、不缩字号，且必须满足：
累计矩阵接近轴对齐、挪移后全文件重叠对总数严格下降、包围盒仍在 viewBox 内。
`--check` 只报告；有残留重叠退出码 1。

用法：
  python3 tools/fix_label_overlap.py --check
  python3 tools/fix_label_overlap.py            # 体检 + 修复
  python3 tools/fix_label_overlap.py --filter 11-diagrams
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtext import (IDENT, VIEWBOX, _mat_mul, _overlap, _to_abs, collect_text_boxes,
                     localname, parse_transform, safe_fromstring, text_local_bbox,
                     xml_guard)

ROOT = Path(__file__).resolve().parent.parent
SKEW_TOL = 1e-3


def analyze(text: str):
    """返回 (pairs, boxes_meta, vw, vh)。
    boxes_meta: [(content, el_ref_chain, abs_box, matrix, fs)]"""
    guard = xml_guard(text)
    if guard:
        return None
    tree = safe_fromstring(text)
    vb = tree.get("viewBox") or ""
    boxes = []

    def walk(el, m, fs):
        tr = el.get("transform")
        if tr:
            m = _mat_mul(m, parse_transform(tr))
        if el.get("font-size"):
            try:
                fs = float(el.get("font-size"))
            except ValueError:
                pass
        if localname(el.tag) == "text":
            content = "".join(el.itertext()).strip()
            if content:
                loc = text_local_bbox(el, content, fs)
                if loc:
                    boxes.append((content, el, _to_abs(loc, m), m, fs))
        for ch in el:
            walk(ch, m, fs)

    walk(tree, IDENT, None)
    vb_m = VIEWBOX.match(vb) if vb else None
    vw = float(vb_m.group(3)) if vb_m else None
    vh = float(vb_m.group(4)) if vb_m else None
    pairs = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _overlap(boxes[i][2], boxes[j][2]):
                pairs.append((i, j))
    return pairs, boxes, vw, vh


def move_y(text: str) -> tuple[str, int]:
    """对每个重叠对尝试把后一枚标签沿 y 挪开；返回 (new_text, fixed_pairs)。"""
    import xml.etree.ElementTree as ETx
    tree = safe_fromstring(text)
    info = analyze(text)
    if not info:
        return text, 0
    pairs, boxes, vw, vh = info
    if not pairs:
        return text, 0
    fixed = 0
    adjusted = set()
    for i, j in pairs:
        content, el, box, m, fs = boxes[j]
        if j in adjusted:
            continue
        a, b, c, d, _e, _f = m
        if abs(c) > SKEW_TOL or abs(b) > SKEW_TOL:
            continue  # 旋转/斜切标签留人工
        step = max(4.0, fs * 0.9)
        done = False
        for k in range(1, 13):
            for sign in (1, -1):
                dy = sign * step * k
                try:
                    y0 = float(el.get("y", "0"))
                except ValueError:
                    break
                el.set("y", f"{y0 + dy:g}")
                new_box = _to_abs(text_local_bbox(el, content, fs), m)
                ok = all(not _overlap(new_box, boxes[k2][2])
                         for k2 in range(len(boxes)) if k2 != j)
                inb = True
                if vw is not None:
                    inb = (new_box[0] >= -0.5 and new_box[1] >= -0.5
                           and new_box[2] <= vw + 0.5 and new_box[3] <= vh + 0.5)
                if ok and inb:
                    fixed += 1
                    adjusted.add(j)
                    done = True
                    break
                el.set("y", f"{y0:g}")
            if done:
                break
    if not fixed:
        return text, 0
    out = ETx.tostring(tree, encoding="unicode")
    if not out.lstrip().startswith("<"):
        return text, 0
    return out, fixed


def main(argv=None):
    ap = argparse.ArgumentParser(description="标签零重叠检查 / 保守修复")
    ap.add_argument("--check", action="store_true", help="只报告不落盘")
    ap.add_argument("--filter", default="")
    args = ap.parse_args(argv)

    base = ROOT / "assets"
    total = 0
    files = []
    for p in sorted(base.rglob("*.svg")):
        if args.filter and args.filter not in str(p.relative_to(ROOT)):
            continue
        text = p.read_text(encoding="utf-8")
        info = analyze(text)
        if info is None:
            continue
        pairs, boxes, vw, vh = info
        if not pairs:
            continue
        total += len(pairs)
        files.append((str(p.relative_to(ROOT)), pairs, boxes))
        print(f"  {p.relative_to(ROOT)}: {len(pairs)} 对重叠")
        for i, j in pairs[:4]:
            print(f"    {boxes[i][0][:18]!r} × {boxes[j][0][:18]!r}")
        if not args.check:
            new_text, fixed = move_y(p.read_text(encoding="utf-8"))
            if fixed:
                p.write_text(new_text, encoding="utf-8")
                print(f"    → 自动挪开 {fixed} 对（已落盘，请复检）")
    print(f"\n标签重叠对合计: {total}（涉及 {len(files)} 个文件）")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
