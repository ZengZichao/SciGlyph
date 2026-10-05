# -*- coding: utf-8 -*-
"""共享 SVG 文本几何工具（自包含，供 legibility / fix_label_overlap / check_repo 使用）。

口径：近似字形度量的包围盒 + 仿射变换累计 + 0.6 pad 重叠判定。
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

VIEWBOX = re.compile(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")
DOCTYPE_RE = re.compile(r"<!DOCTYPE|<!ENTITY", re.I)
MAX_SVG_BYTES = 5_000_000
SVG_NS = "http://www.w3.org/2000/svg"
NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def xml_guard(raw: str):
    if len(raw) > MAX_SVG_BYTES:
        return f"文件超过 {MAX_SVG_BYTES} 字节上限"
    if DOCTYPE_RE.search(raw):
        return "包含 <!DOCTYPE>/<!ENTITY>（实体扩展防护）"
    return None


def safe_fromstring(src: str):
    if DOCTYPE_RE.search(src):
        raise ET.ParseError("DOCTYPE/ENTITY 不允许（实体扩展防护）")
    parser = ET.XMLParser()
    xp = getattr(parser, "parser", None)
    if xp is not None:
        def _reject(*_a):
            raise ET.ParseError("DOCTYPE/ENTITY 不允许（实体扩展防护）")
        xp.StartDoctypeDeclHandler = _reject
        xp.EntityDeclHandler = _reject
    parser.feed(src)
    return parser.close()


def localname(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else str(tag)


def _mat_mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
TRANS = re.compile(r"(translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def parse_transform(tr):
    if not tr:
        return IDENT
    m = IDENT
    for name, args in TRANS.findall(tr):
        try:
            v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x != ""]
        except ValueError:
            return m
        if name == "translate":
            c = (1.0, 0.0, 0.0, 1.0, v[0] if v else 0.0, v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            sx = v[0] if v else 1.0
            c = (sx, 0.0, 0.0, v[1] if len(v) > 1 else sx, 0.0, 0.0)
        elif name == "rotate":
            if not v:
                continue
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            rot = (ca, sa, -sa, ca, 0.0, 0.0)
            if len(v) > 2:
                cx, cy = v[1], v[2]
                c = _mat_mul(_mat_mul((1, 0, 0, 1, cx, cy), rot), (1, 0, 0, 1, -cx, -cy))
            else:
                c = rot
        elif name == "skewX":
            c = (1.0, 0.0, math.tan(math.radians(v[0])) if v else 0.0, 1.0, 0.0, 0.0)
        elif name == "skewY":
            c = (1.0, math.tan(math.radians(v[0])) if v else 0.0, 0.0, 1.0, 0.0, 0.0)
        else:
            continue
        m = _mat_mul(m, c)
    return m


def _apply_mat(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def text_local_bbox(el, content, fs):
    """文字在自身局部坐标下的包围盒（近似字形度量）。"""
    if not fs:
        return None
    cjk = sum(1 for ch in content if ord(ch) > 0x2E80)
    w = (len(content) - cjk) * 0.60 * fs + cjk * 1.02 * fs
    try:
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
    except ValueError:
        return None
    anchor = (el.get("text-anchor") or "start").lower()
    if anchor == "middle":
        x0, x1 = x - w / 2.0, x + w / 2.0
    elif anchor in ("end", "right"):
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    return (x0, y - 0.72 * fs, x1, y + 0.20 * fs)


def _to_abs(box, m):
    pts = [_apply_mat(m, box[0], box[1]), _apply_mat(m, box[2], box[1]),
           _apply_mat(m, box[0], box[3]), _apply_mat(m, box[2], box[3])]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _overlap(a, b, pad=0.6):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0]
                or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def collect_text_boxes(tree, vb=None):
    """累计祖先 transform/font-size，收集全部 <text> 绝对包围盒。

    返回 [(content, abs_box, font_size)]。vb 传入 viewBox 字符串时同时给出 (vw, vh)。
    """
    vb_m = VIEWBOX.match(vb) if vb else None
    vw = vh = None
    if vb_m:
        vw, vh = float(vb_m.group(3)), float(vb_m.group(4))
    boxes = []

    def walk(el, m, fs):
        tr = el.get("transform")
        if tr:
            m = _mat_mul(m, parse_transform(tr))
        if el.get("font-size"):
            try:
                fs = float(re.sub(r"[a-z%]+$", "", el.get("font-size")))
            except ValueError:
                pass
        if localname(el.tag) == "text":
            content = "".join(el.itertext()).strip()
            eff = fs
            if el.get("font-size"):
                try:
                    eff = float(re.sub(r"[a-z%]+$", "", el.get("font-size")))
                except ValueError:
                    eff = fs
            if content:
                loc = text_local_bbox(el, content, eff)
                if loc:
                    boxes.append((content, _to_abs(loc, m), eff))
        for ch in el:
            walk(ch, m, fs)

    walk(tree, IDENT, None)
    return boxes, (vw, vh)


def has_cjk_text(tree) -> bool:
    """渲染文本（text/tspan 直content）是否含 CJK。title/desc 不计。"""
    for el in tree.iter():
        if localname(el.tag) in ("text", "tspan"):
            content = "".join(el.itertext()).strip()
            if any(ord(c) > 0x2E80 for c in content):
                return True
    return False
