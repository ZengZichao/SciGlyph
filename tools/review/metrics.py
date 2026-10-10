# -*- coding: utf-8 -*-
"""素材级客观度量与异常检测（纯标准库）。

对全部 SVG 逐文件测量几何/排印/配色结构，输出可用于人工复核的异常清单：
  - 画布占比 / 重心偏移 / 越界范围（由图元坐标并集近似）
  - 文字：字号、字重、锚点、按 CJK=1.0 / Latin=0.58 估算的宽度占比
  - 配色：字面 hex 集合、离群色（全库出现次数极少）、currentColo/外链/脚本
  - 结构：重复签名（同一子目录与跨子目录）、空分组、无 title/desc
输出：qa/review/metrics.json（逐文件）+ qa/review/anomalies.md（分组摘要）

用法：python tools/review/metrics.py [--cat 01-cells-microbes]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUT = ROOT / "qa" / "review"

NUM = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")
HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")


def strip_ns(tag):
    return tag.rsplit("}", 1)[-1]


def parse_transform(t):
    """返回 3x2 仿射矩阵 (a,b,c,d,e,f)：x'=a*x+c*y+e, y'=b*x+d*y+f。"""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, arg in re.findall(r"(translate|scale|rotate|skewX|skewY|matrix)\(([^)]*)\)", t or ""):
        v = [float(x) for x in NUM.findall(arg)]
        if name == "translate":
            n = mat_mul((1, 0, 0, 1, v[0] if v else 0, v[1] if len(v) > 1 else 0), m)
        elif name == "scale":
            n = mat_mul((v[0] if v else 1, 0, 0, v[1] if len(v) > 1 else (v[0] if v else 1), 0, 0), m)
        elif name == "rotate":
            import math
            a = math.radians(v[0]) if v else 0.0
            ca, sa = math.cos(a), math.sin(a)
            n = mat_mul((ca, sa, -sa, ca, 0, 0), m)
            if len(v) == 3:
                n = mat_mul((1, 0, 0, 1, v[2], v[1]), mat_mul(n, (1, 0, 0, 1, -v[1], -v[2])))
        elif name == "skewX":
            import math
            n = mat_mul((1, 0, math.tan(math.radians(v[0] if v else 0)), 1, 0, 0), m)
        elif name == "skewY":
            import math
            n = mat_mul((1, math.tan(math.radians(v[0] if v else 0)), 0, 1, 0, 0), m)
        else:
            n = mat_mul(tuple(v[:6]), m) if len(v) >= 6 else m
        m = n
    return m


def mat_mul(a, b):
    """a 后接 b（b 为外层已生效矩阵）：结果 = A x B。"""
    a1, a2, a3, a4, a5, a6 = a
    b1, b2, b3, b4, b5, b6 = b
    return (a1 * b1 + a3 * b2, a2 * b1 + a4 * b2,
            a1 * b3 + a3 * b4, a2 * b3 + a4 * b4,
            a1 * b5 + a3 * b6 + a5, a2 * b5 + a4 * b6 + a6)


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


CMD_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def path_points(d):
    """按 SVG 路径语法走笔，返回绝对坐标采样点（端点 + 曲线上的细分点）。"""
    import math
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d+(?:\.\d+)?(?:e-?\d+)?", d or "")
    pts, cx, cy, sx, sy = [], 0.0, 0.0, 0.0, 0.0
    i, cmd = 0, ""
    while i < len(toks):
        t = toks[i]
        if not re.match(r"-?\d", t):
            cmd = t
            i += 1
            continue
        upper = cmd.upper()
        rel = cmd.islower()
        need = CMD_ARGS.get(upper, 2)
        vals = []
        j = i
        while j < len(toks) and len(vals) < need and re.match(r"-?\d", toks[j]):
            vals.append(float(toks[j]))
            j += 1
        if len(vals) < need:
            break
        i = j
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if upper == "M":
            cx, cy = ox + vals[0], oy + vals[1]
            sx, sy = cx, cy
            pts.append((cx, cy))
            cmd = ("l" if rel else "L")
        elif upper == "L":
            cx, cy = ox + vals[0], oy + vals[1]
            pts.append((cx, cy))
        elif upper == "H":
            cx = ox + vals[0]
            pts.append((cx, cy))
        elif upper == "V":
            cy = oy + vals[0]
            pts.append((cx, cy))
        elif upper == "C":
            x1, y1, x2, y2, x, y = [v + o for v, o in zip(vals, (ox, oy, ox, oy, ox, oy))]
            for k in range(1, 11):
                u = k / 10
                mt = 1 - u
                pts.append((mt**3 * cx + 3 * mt**2 * u * x1 + 3 * mt * u**2 * x2 + u**3 * x,
                            mt**3 * cy + 3 * mt**2 * u * y1 + 3 * mt * u**2 * y2 + u**3 * y))
            cx, cy = x, y
        elif upper == "S" or upper == "T":
            x, y = ox + vals[-2], oy + vals[-1]
            pts.append((x, y))
            cx, cy = x, y
        elif upper == "Q":
            x1, y1, x, y = [v + o for v, o in zip(vals, (ox, oy, ox, oy))]
            for k in range(1, 11):
                u = k / 10
                mt = 1 - u
                pts.append((mt * mt * cx + 2 * mt * u * x1 + u * u * x,
                            mt * mt * cy + 2 * mt * u * y1 + u * u * y))
            cx, cy = x, y
        elif upper == "A":
            rx, ry, rot, fa, fs, x, y = vals
            x, y = ox + x, oy + y
            pts.append((x, y))
            cx, cy = x, y
        elif upper == "Z":
            cx, cy = sx, sy
        if upper != "M" and need:
            pass
    return pts


def point_box(el, mat):
    """返回该图元变换后的近似包围盒 (minx, miny, maxx, maxy)。"""
    tag = strip_ns(el.tag)
    a = el.attrib
    f = lambda k, d=0.0: float(a.get(k, d) or d)
    pts = []
    if tag in ("rect", "image"):
        x, y = f("x"), f("y")
        w, h = f("width"), f("height")
        if w and h:
            pts = [(x, y), (x + w, y + h)]
    elif tag == "circle":
        cxp, cyp, r = f("cx"), f("cy"), f("r")
        pts = [(cxp - r, cyp - r), (cxp + r, cyp + r)]
    elif tag == "ellipse":
        cxp, cyp = f("cx"), f("cy")
        rx, ry = f("rx"), f("ry", f("rx"))
        pts = [(cxp - rx, cyp - ry), (cxp + rx, cyp + ry)]
    elif tag == "line":
        pts = [(f("x1"), f("y1")), (f("x2"), f("y2"))]
    elif tag in ("polygon", "polyline"):
        v = [float(x) for x in NUM.findall(a.get("points", ""))]
        pts = list(zip(v[0::2], v[1::2]))
    elif tag == "path":
        pts = path_points(a.get("d", ""))
    elif tag == "text":
        x, y = f("x"), f("y")
        fs = font_size(a, ()) or 3.0
        s_ = "".join(el.itertext())
        w = est_width(s_, fs)
        anchor = a.get("text-anchor", "start")
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        pts = [(x0, y - fs * 0.8), (x0 + w, y + fs * 0.25)]
    if not pts:
        return None
    out = [apply(mat, px, py) for (px, py) in pts]
    xs = [p[0] for p in out]
    ys = [p[1] for p in out]
    return (min(xs), min(ys), max(xs), max(ys))


def font_size(a, inherited):
    v = a.get("font-size")
    if v:
        m = NUM.search(v)
        if m:
            return float(m.group())
    return inherited[4] if len(inherited) > 4 else 3.0


def est_width(s, fs):
    if not fs:
        return 0.0
    units = 0.0
    for ch in s:
        if CJK.match(ch):
            units += 1.0
        elif ch in "iljt.,:;'!|()[] ":
            units += 0.30
        elif ch.isupper():
            units += 0.72
        else:
            units += 0.55
    return units * fs


def walk(el, mat, base_fs, acc):
    tag = strip_ns(el.tag)
    a = el.attrib
    cur = mat_mul(parse_transform(a.get("transform", "")), mat)
    fs = font_size(a, ())
    base = fs if fs else base_fs
    acc["tags"][tag] += 1
    if tag == "text":
        s = " ".join("".join(el.itertext()).split())
        acc["texts"].append({
            "s": s,
            "fs": base * abs(cur[0] if cur[0] else 1),
            "anchor": a.get("text-anchor", "start"),
            "weight": a.get("font-weight", ""),
            "fill": a.get("fill", ""),
        })
    for k in ("fill", "stroke"):
        v = a.get(k)
        if v:
            acc["paints"][v] += 1
    b = point_box(el, cur)
    if b:
        acc["boxes"].append(b)
    for ch in el:
        walk(ch, cur, base, acc)


def analyze(path: Path, view):
    import xml.etree.ElementTree as ET
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except Exception:
        return {"error": "parse"}
    acc = {"tags": Counter(), "texts": [], "paints": Counter(), "boxes": []}
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 3.0, acc)
    vw = view.get("w", 0)
    vh = view.get("h", 0)
    boxes = acc["boxes"]
    if boxes:
        bb = (min(b[0] for b in boxes), min(b[1] for b in boxes),
              max(b[2] for b in boxes), max(b[3] for b in boxes))
    else:
        bb = (0, 0, 0, 0)
    fill = 0.0
    if vw and vh:
        fw = min(bb[2], vw) - max(bb[0], 0)
        fh = min(bb[3], vh) - max(bb[1], 0)
        inside = max(fw, 0) * max(fh, 0)
        gross = max(bb[2] - bb[0], 0) * max(bb[3] - bb[1], 0)
        fill = inside / (vw * vh)
        cover_of_content = inside / gross if gross else 1.0
    else:
        cover_of_content = 1.0
    cx = (bb[0] + bb[2]) / 2
    cy = (bb[1] + bb[3]) / 2
    hexes = {p for p in acc["paints"] if HEX.fullmatch(p or "x") or HEX.match(p or "")}
    title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", raw, re.S)
    sig = hashlib.sha1(json.dumps(
        sorted([tuple(round(x, 1) for x in b) for b in boxes]) +
        [t["s"] for t in acc["texts"]], ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return {
        "view": [vw, vh],
        "bbox": [round(x, 1) for x in bb],
        "fill": round(fill, 3),
        "cover": round(cover_of_content, 3),
        "offx": round(abs(cx - vw / 2) / vw, 3) if vw else 0,
        "offy": round(abs(cy - vh / 2) / vh, 3) if vh else 0,
        "n_el": sum(acc["tags"].values()),
        "n_text": len(acc["texts"]),
        "min_fs": round(min([t["fs"] for t in acc["texts"]], default=0), 2),
        "texts": [t["s"] for t in acc["texts"]],
        "fs_list": sorted({t["fs"] for t in acc["texts"]}),
        "colors": sorted(hexes),
        "n_colors": len(hexes),
        "currentcolor": "currentColor" in raw,
        "style_tag": "<style" in raw,
        "script": "<script" in raw,
        "external": bool(re.search(r'(?:xlink:href|href)="https?://', raw)),
        "embed": "base64" in raw,
        "title": (title.group(1).strip() if title else ""),
        "desc": (desc.group(1).strip()[:220] if desc else ""),
        "sig": sig,
    }


def read_view(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'viewBox="([^"]+)"', raw)
    if not m:
        return {"w": 0, "h": 0, "raw": ""}
    p = m.group(1).split()
    return {"w": float(p[2]), "h": float(p[3]), "raw": m.group(1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    OUT.mkdir(parents=True, exist_ok=True)
    docs = {}
    all_colors = Counter()
    sig_by_file = defaultdict(list)
    for sub in sorted(ASSETS.glob("*/*/")):
        if args.cat and not sub.parent.name.startswith(args.cat):
            continue
        for f in sorted(sub.glob("*.svg")):
            v = read_view(f)
            r = analyze(f, v)
            r["cat"] = sub.parent.name
            r["sub"] = sub.name
            r["file"] = f.name
            docs[f.relative_to(ROOT).as_posix()] = r
            for c in r.get("colors", []):
                all_colors[c.upper()] += 1
            sig_by_file[r["sig"]].append(f.relative_to(ROOT).as_posix())

    rare = {c for c, n in all_colors.items() if n <= 2}
    dups = {k: v for k, v in sig_by_file.items() if len(v) > 1}
    flags = defaultdict(list)
    for p, r in docs.items():
        if r.get("error"):
            flags["parse-error"].append(p)
            continue
        if r["fill"] < 0.06:
            flags["too-small-on-canvas"].append(p)
        if r["fill"] > 0.85:
            flags["crowded-canvas"].append(p)
        if r["cover"] < 0.45:
            flags["sparse-bbox"].append(p)
        if r["offx"] > 0.10 or r["offy"] > 0.10:
            flags["off-center"].append(p)
        if r["bbox"][0] < -1 or r["bbox"][1] < -1 or r["bbox"][2] > r["view"][0] + 1 or r["bbox"][3] > r["view"][1] + 1:
            flags["geometry-out-of-viewbox"].append(p)
        if r["n_text"] == 0 and r["cat"].startswith(("01", "02", "03", "04", "05", "06", "11")) and r["n_el"] > 40:
            flags["complex-but-unlabeled"].append(p)
        if 0 < r["min_fs"] < 2.2:
            flags["tiny-font"].append(p)
        if r["currentcolor"]:
            flags["currentcolor"].append(p)
        if r["style_tag"]:
            flags["style-tag"].append(p)
        if r["external"]:
            flags["external-ref"].append(p)
        if r["embed"]:
            flags["embedded-raster"].append(p)
        if len(set(r["colors"])) >= 14:
            flags["color-heavy"].append(p)
        oc = [c for c in r["colors"] if c.upper() in rare]
        if oc:
            flags["rare-color"].append(p)

    report = {
        "n_files": len(docs),
        "flags": {k: sorted(v) for k, v in sorted(flags.items())},
        "counts": {k: len(v) for k, v in sorted(flags.items())},
        "duplicate_signatures": dups,
        "rare_colors": sorted(rare),
        "per_file": docs,
    }
    (OUT / "metrics.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    lines = ["# 素材客观度量异常摘要", ""]
    lines.append(f"扫描文件：{len(docs)}；重复签名组：{len(dups)}")
    for k, v in sorted(flags.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n## {k}（{len(v)}）\n")
        for p in sorted(v)[:400]:
            r = docs[p]
            lines.append(f"- {p} fill={r['fill']} bbox={r['bbox']} n_text={r['n_text']} min_fs={r['min_fs']} colors={r['n_colors']}")
    (OUT / "anomalies.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))
    print("dups", len(dups), "rare_colors", len(rare), "files", len(docs))


if __name__ == "__main__":
    main()
