#!/usr/bin/env python3
"""文字出画修复器（zh 与 en 全量适用）。

Pass A（raw 级 reflow）：字号降到下限；仍超宽则按空格换行（CJK 无空格时按 ≤10 字硬切），
多行重建为干净的 <text>（仅对无 transform 祖先的标签——有 transform 时 raw 平移会失真）。
Pass B（矩阵感知）：对仍出画的标签，用累计逆矩阵把目标盒位映射回局部坐标平移；
行宽超画布的（单词过长等）保留并报告。

用法：python3 tools/fix_text_overflow.py [--filter 串]
退出码：0 = 全部修复；1 = 仍有残留（打印清单）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import fix_label_overlap as flo  # noqa: E402
import legibility as leg  # noqa: E402
from svgtext import _to_abs, safe_fromstring, text_local_bbox  # noqa: E402
from fix_labels_manual import mat_inv  # noqa: E402

TEXT_BLOCK = re.compile(r"<text\b[^>]*>.*?</text>|<text\b[^>]*/>", re.S)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def vb_of(raw):
    m = re.search(r'viewBox="([^"]+)"', raw)
    if not m:
        return None
    v = [float(x) for x in m.group(1).replace(",", " ").split()]
    # 归一为 (x0, y0, x1, y1)，支持非零原点
    return v[0], v[1], v[0] + v[2], v[1] + v[3]


def wrap_lines(content, use, allowed):
    if " " in content:
        words = content.split(" ")
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if leg.measure(trial, use) <= allowed or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines
    # CJK / 无空格：按宽度硬切
    lines, cur = [], ""
    for ch in content:
        if leg.measure(cur + ch, use) > allowed and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def pass_a(raw: str) -> str:
    vb = vb_of(raw)
    if not vb:
        return raw
    vx0, vy0, vx1, vy1 = vb
    vw, vh = vx1 - vx0, vy1 - vy0
    floor = leg.floor_for(max(vw, vh))
    allowed = vw - 1.0
    out = raw

    def fix_block(m):
        tag = m.group(0)
        a = dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]))
        if "font-size" not in a or "transform" in a:
            return tag
        fs = float(a["font-size"])
        content = re.sub(r"<[^>]+>", "", tag)
        anchor = a.get("text-anchor", "start")
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        use = fs
        w = leg.measure(content, use)
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor in ("end", "right") else x)
        if vx0 + 0.5 <= x0 and x0 + w <= vx1 - 0.5:
            return tag
        if use > floor:
            use = floor
            w = leg.measure(content, use)
            x0 = x - w / 2 if anchor == "middle" else (x - w if anchor in ("end", "right") else x)
        if vx0 + 0.5 <= x0 and x0 + w <= vx1 - 0.5:
            return tag.replace(f'font-size="{leg.a_num(fs)}"', f'font-size="{leg.a_num(use)}"', 1)
        if w > allowed:
            lines = wrap_lines(content, use, allowed)
            if any(leg.measure(ln, use) > allowed for ln in lines):
                return tag
            open_tag = tag[: tag.index(">")]
            open_tag = re.sub(r'\s+(x|y|font-size)="[^"]*"', "", open_tag)
            open_tag += f' font-size="{leg.a_num(use)}"'
            pieces = []
            for i, ln in enumerate(lines):
                lw = leg.measure(ln, use)
                lx = x - lw / 2 if anchor == "middle" else (x - lw if anchor in ("end", "right") else x)
                lx = min(max(lx, vx0 + 0.5), max(vx0 + 0.5, vx1 - lw - 0.5))
                ly = y + i * use * 1.18
                pieces.append(f'{open_tag} x="{round(lx, 2)}" y="{round(ly, 2)}">{ln}</text>')
            return "".join(pieces)
        # 行宽可容但位置出界：平移锚点
        dx = 0.0
        if x0 < vx0 + 0.5:
            dx = (vx0 + 0.5) - x0
        elif x0 + w > vx1 - 0.5:
            dx = (vx1 - 0.5) - (x0 + w)
        new_tag = tag.replace(f'font-size="{leg.a_num(fs)}"', f'font-size="{leg.a_num(use)}"', 1)
        return re.sub(r'([\s])x="[^"]*"', rf'\g<1>x="{round(x + dx, 2)}"', new_tag, count=1)

    for _ in range(2):
        new = TEXT_BLOCK.sub(fix_block, out)
        if new == out:
            break
        out = new
    return out


def pass_b(p: Path) -> int:
    """矩阵感知的钳位平移；返回修复的标签数。"""
    raw = p.read_text(encoding="utf-8")
    info = flo.analyze(raw)
    if not info:
        return 0
    pairs, boxes, _vw, _vh = info
    vb = vb_of(raw)
    if not vb or not boxes:
        return 0
    vx0, vy0, vx1, vy1 = vb
    vw, vh = vx1 - vx0, vy1 - vy0
    fixed = 0
    for content, el, box, m, fs in boxes:
        if not (box[0] < -0.5 or box[1] < -0.5 or box[2] > vw + 0.5 or box[3] > vh + 0.5):
            continue
        w = box[2] - box[0]
        h = box[3] - box[1]
        if w > vw - 1:
            continue  # 行本身太长，Pass A 已尽力
        inv = mat_inv(m)
        if inv is None:
            continue
        nx = min(max(box[0], vx0 + 0.5), max(vx0 + 0.5, vx1 - w - 0.5))
        ny = min(max(box[1], vy0 + 0.5), max(vy0 + 0.5, vy1 - h - 0.5))
        l0 = text_local_bbox(el, content, fs)
        if not l0:
            continue
        lx = inv[0] * nx + inv[2] * ny + inv[4]
        ly = inv[1] * nx + inv[3] * ny + inv[5]
        dx, dy = lx - l0[0], ly - l0[1]
        if abs(dx) < 0.05 and abs(dy) < 0.05:
            continue
        try:
            old_x, old_y = float(el.get("x", "0")), float(el.get("y", "0"))
        except ValueError:
            continue
        new_x, new_y = old_x + dx, old_y + dy
        done = [False]
        pat = re.compile(r"<text\b[^>]*>.*?</text>|<text\b[^>]*/>", re.S)

        def sub(mm):
            if done[0]:
                return mm.group(0)
            tag = mm.group(0)
            d = dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]))
            if d.get("x") is None or d.get("y") is None:
                return tag
            raw_content = re.sub(r"<[^>]+>", "", tag).strip()
            raw_content = (raw_content.replace("&lt;", "<").replace("&gt;", ">")
                           .replace("&amp;", "&").replace("&quot;", '"').replace("&apos;", "'"))
            try:
                if (abs(float(d["x"]) - old_x) < 1e-6 and abs(float(d["y"]) - old_y) < 1e-6
                        and raw_content == content):
                    done[0] = True
                    tag = re.sub(r'([\s])x="[^"]*"', rf'\g<1>x="{round(new_x, 2)}"', tag, count=1)
                    return re.sub(r'([\s])y="[^"]*"', rf'\g<1>y="{round(new_y, 2)}"', tag, count=1)
            except ValueError:
                return tag
            return tag

        raw = pat.sub(sub, raw)
        fixed += 1
    if fixed:
        p.write_text(raw, encoding="utf-8")
    return fixed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="")
    args = ap.parse_args(argv)
    residual = []
    for p in sorted((ROOT / "assets").rglob("*.svg")):
        rel = str(p.relative_to(ROOT))
        if args.filter and args.filter not in rel:
            continue
        raw = p.read_text(encoding="utf-8")
        new = pass_a(raw)
        if new != raw:
            p.write_text(new, encoding="utf-8")
        for _ in range(3):
            n = pass_b(p)
            if not n:
                break
        # 复查
        info = flo.analyze(p.read_text(encoding="utf-8"))
        if info:
            _pairs, boxes, vw, vh = info
            if vw is not None:
                bad = [b for c, _e, b, _m, _f in boxes
                       if b[0] < -0.5 or b[1] < -0.5 or b[2] > vw + 0.5 or b[3] > vh + 0.5]
                if bad:
                    residual.append((rel, bad[0]))
    if residual:
        print(f"残留出画 {len(residual)}：")
        for rel, b in residual[:30]:
            print("  ", rel, [round(v) for v in b])
        return 1
    print("文字出画全部修复")
    return 0


if __name__ == "__main__":
    sys.exit(main())
