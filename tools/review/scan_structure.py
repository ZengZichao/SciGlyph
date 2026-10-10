# -*- coding: utf-8 -*-
"""结构性缺陷扫描：素材在真实渲染器里"画不出来"的所有情形。

check_repo.py 只看命名/许可/文字，不看图元是否真的会被渲染。本脚本补这一段，
逐文件报告：
  1. 根 <svg> 缺 xmlns          —— 浏览器/PPT/Figma 整张不渲染；
  2. 标签用错属性                —— 如 <rect d="...">，图元被忽略；
  3. 零面积不可见图元            —— line/polyline/path 只有 fill 没有可见描边；
  4. 透明到看不见                —— opacity / fill-opacity / stroke-opacity 为 0 或 <0.05；
  5. 重复 id / aria-labelledby 悬空引用；
  6. 尺寸与 viewBox 比例不一致   —— width/height 与 viewBox 长宽比不符，导出会变形。

用法：
  python tools/review/scan_structure.py            # 只报告
  python tools/review/scan_structure.py --fix      # 能安全自动修的直接修
输出 qa/review/structure.json + 控制台摘要。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

VALID = {
    "rect": {"x", "y", "width", "height", "rx", "ry"},
    "circle": {"cx", "cy", "r"},
    "ellipse": {"cx", "cy", "rx", "ry"},
    "line": {"x1", "y1", "x2", "y2"},
    "polygon": {"points"},
    "polyline": {"points"},
    "path": {"d"},
    "text": {"x", "y", "dx", "dy", "text-anchor", "transform"},
}
COMMON = {"fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity",
          "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "transform", "id",
          "class", "style", "font-family", "font-size", "font-weight", "data-pp",
          "data-ls", "data-name", "data-license", "data-copyright", "visibility", "display",
          "aria-labelledby", "role", "marker-end", "marker-start", "clip-path", "fill-rule",
          "vector-effect", "dominant-baseline", "text-anchor", "letter-spacing", "paint-order"}
GEOM_TAGS = set(VALID) - {"text"}
SHAPE_TAGS = {"line", "polyline", "polygon", "path", "rect", "circle", "ellipse"}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def num(v):
    try:
        return float(re.sub(r"[a-z%]+$", "", str(v)))
    except Exception:
        return None


def scan(path: Path):
    raw = path.read_text(encoding="utf-8")
    issues = []
    m_head = re.search(r"<svg\b[^>]*>", raw, re.S)
    head = m_head.group(0) if m_head else ""
    if "xmlns=" not in head:
        issues.append("no-xmlns")
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        return ["xml-parse-error:" + str(e)[:60]], 0
    ids = Counter()

    def walk(el, style):
        tag = local(el.tag)
        a = el.attrib
        st = dict(style)
        for k in ("fill", "stroke", "opacity", "fill-opacity", "stroke-opacity", "stroke-width"):
            if k in a:
                st[k] = a[k]
        for k, v in a.items():
            ln = local(k)
            if tag in VALID and ln == "d" and tag != "path":
                issues.append(f"attr-mismatch:{tag}@d")
            if (tag in VALID and ln in ("cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2",
                                        "points", "width", "height")
                    and ln not in VALID[tag] | COMMON):
                issues.append(f"attr-mismatch:{tag}@{ln}")
        if "id" in a:
            ids[a["id"]] += 1

        def transparent(key, default="1"):
            v = num(a.get(key, st.get(key, default)))
            return v is not None and v < 0.05

        alpha_zero = transparent("opacity") or (transparent("fill-opacity") and
                                                transparent("stroke-opacity"))
        if alpha_zero:
            issues.append(f"near-zero-alpha:{tag}")
        if tag in GEOM_TAGS and a.get("visibility") == "hidden":
            issues.append(f"hidden-shape:{tag}")
        if tag in ("line", "polyline", "polygon", "path"):
            stroke = st.get("stroke", a.get("stroke", "none"))
            fill = st.get("fill", a.get("fill", "black"))
            no_stroke = stroke in (None, "", "none")
            no_fill = fill in (None, "", "none")
            if tag in ("line", "polyline") and no_stroke:
                issues.append(f"invisible-open-shape:{tag}")
            elif tag == "path" and no_stroke and no_fill:
                issues.append("invisible-path:no-fill-no-stroke")
            elif not no_stroke and not alpha_zero:
                pass
        for ch in el:
            walk(ch, st)

    walk(root, {})
    for i, c in ids.items():
        if c > 1:
            issues.append(f"duplicate-id:{i}x{c}")
    lab = re.search(r'aria-labelledby="([^"]+)"', raw)
    if lab:
        for ref in lab.group(1).split():
            if f'id="{ref}"' not in raw:
                issues.append(f"dangling-aria:{ref}")
    vb = re.search(r'viewBox="([^"]+)"', head)
    w_m, h_m = re.search(r'width="([^"]+)"', head), re.search(r'height="([^"]+)"', head)
    if vb and w_m and h_m:
        p = [float(x) for x in vb.group(1).split()]
        w, h = num(w_m.group(1)), num(h_m.group(1))
        if len(p) == 4 and w and h and p[3]:
            if abs((w / h) - (p[2] / p[3])) > 0.01 * max(1.0, p[2] / p[3]):
                issues.append(f"aspect-mismatch:{w_m.group(1)}x{h_m.group(1)} vs {vb.group(1)}")
    return sorted(set(issues)), len(list(root.iter()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--cat", default="")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    bad = {}
    kinds = Counter()
    fixed = Counter()
    files = sorted(ASSETS.glob("*/*/*.svg"))
    if args.cat:
        files = [f for f in files if f.parent.parent.name.startswith(args.cat)]
    for f in files:
        issues, _ = scan(f)
        if not issues:
            continue
        raw = f.read_text(encoding="utf-8")
        before = list(issues)
        if args.fix:
            # 1) 缺 xmlns：补标准命名空间（对渲染是必需且无副作用）
            if "no-xmlns" in issues:
                raw = raw.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
                issues.remove("no-xmlns")
                fixed["no-xmlns"] += 1
            # 2) <rect d="..."> 这类错标签：rect 的 d 是无效属性，改成 path 才能渲染
            if any(i.startswith("attr-mismatch:rect@d") for i in issues):
                raw = re.sub(r"<rect\b([^>]*?)\sd=\"([^\"]+)\"([^>]*?)/>",
                             lambda m: f'<path{m.group(1)} d="{m.group(2)}"{m.group(3)}/>', raw)
                issues = [i for i in issues if not i.startswith("attr-mismatch:rect@d")]
                fixed["rect@d->path"] += 1
            f.write_text(raw, encoding="utf-8", newline="")
        if issues:
            key = str(f.relative_to(ROOT)).replace("\\", "/")
            bad[key] = issues
            for i in before:
                kinds[i.split(":")[0]] += 1
    (ROOT / "qa" / "review" / "structure.json").write_text(
        json.dumps({"n_files": len(files), "bad": bad, "kinds": dict(kinds),
                    "auto_fixed": dict(fixed)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("扫描", len(files), "个文件；仍有问题", len(bad))
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")
    if args.fix:
        print("自动修复:", dict(fixed))
    for k, v in list(bad.items())[:40]:
        print("  -", k, v)


if __name__ == "__main__":
    main()
