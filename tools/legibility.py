#!/usr/bin/env python3
"""文字印刷字高下限检查（新结构版，扫描 assets/）。

口径：1 viewBox 单位 = 1 CSS px = 0.2646mm；正文标注最低 1.7mm ⇒ font-size ≥ 7；
微型图标（画布较大边 < 64 单位）放宽到 4。

`--fix` 只把字号**放大**到下限，且必须同时满足：盒子不出画布、不与其它 <text> 相交；
放不了的原样保留并列入报告（人工重排或删标签），不静默放过。

用法：
  python3 tools/legibility.py                     # 全库体检（有任何低于下限 → 退出码 1）
  python3 tools/legibility.py --fix               # 安全放大
  python3 tools/legibility.py --filter 09-safety  # 只处理路径含该串的文件
  python3 tools/legibility.py --json tools/legibility-report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_RE = re.compile(r"<text\b[^>]*?(?:/>|>.*?</text>)", re.S)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
MM_PER_UNIT = 0.2646
TARGET_MM = 1.7
CHAR_W = 0.62
CJK_W = 1.0


def floor_for(canvas: float) -> float:
    base = TARGET_MM / MM_PER_UNIT
    return 4.0 if canvas < 64 else float(int(round(base)) + 1)   # →7


def is_cjk(s: str) -> bool:
    return any(ord(c) > 0x2E00 for c in s)


def measure(text: str, fs: float):
    wide = sum(CHAR_W if not is_cjk(ch) else CJK_W for ch in text)
    return fs * wide


def a_num(v: float) -> str:
    return f"{v:g}"


def boxes(s: str, floor: float):
    out = []
    for m in TEXT_RE.finditer(s):
        tag = m.group(0)
        a = dict(ATTR_RE.findall(tag[: tag.index(">") + 1]))
        if "font-size" not in a:
            continue
        try:
            fs = float(a["font-size"])
        except ValueError:
            continue
        try:
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
        except ValueError:
            continue
        content = re.sub(r"<[^>]+>", "", tag)
        content = re.sub(r"^.*?>", "", content, count=1, flags=re.S)
        use = max(fs, floor)
        w = measure(content, use)
        anchor = a.get("text-anchor", "start")
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        out.append((m.start(), m.end(), tag,
                    (x0, y - use * 0.8, x0 + w, y + use * 0.2), fs))
    return out


def overlap(b1, b2) -> bool:
    return not (b1[2] <= b2[0] + 0.5 or b2[2] <= b1[0] + 0.5
                or b1[3] <= b2[1] + 0.5 or b2[3] <= b1[1] + 0.5)


def process(text: str, fix=False):
    """返回 (new_text, below, refused, raised)。below=低于下限清单，refused=不能自动放大清单。"""
    vb = re.search(r'viewBox="([^"]+)"', text)
    if not vb:
        return text, [], [], []
    nums = [float(v) for v in vb.group(1).replace(",", " ").split()]
    canvas = max(nums[2], nums[3])
    floor = floor_for(canvas)
    bs = boxes(text, floor)
    if not bs:
        return text, [], [], []
    edits, refused, below, raised = [], [], [], []
    for i, (s0, s1, tag, box, fs) in enumerate(bs):
        if fs < floor:
            below.append((fs, floor, re.sub(r"<[^>]+>", "", tag)[:24]))
        if fs >= floor:
            continue
        clash = False
        for j, (_s0, _s1, _t, b2, _f2) in enumerate(bs):
            if j != i and overlap(box, b2):
                clash = True
                break
        x0, y0, x1, y1 = box
        if (x0 < 0 or y0 < 0 or x1 > canvas + 0.5 or y1 > canvas + 0.5) and canvas >= 64:
            clash = True
        if clash:
            refused.append((fs, floor, re.sub(r"<[^>]+>", "", tag)[:24]))
            continue
        new_tag = tag.replace(f'font-size="{a_num(fs)}"', f'font-size="{a_num(floor)}"', 1)
        if new_tag == tag:
            refused.append((fs, floor, re.sub(r"<[^>]+>", "", tag)[:24]))
            continue
        edits.append((s0, s1, new_tag))
        raised.append((fs, floor))
    if fix and edits:
        for s0, s1, new_tag in sorted(edits, key=lambda e: -e[0]):
            text = text[:s0] + new_tag + text[s1:]
    return text, below, refused, raised


def main(argv=None):
    ap = argparse.ArgumentParser(description="文字可读性下限检查 / 安全放大")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--filter", default="", help="只处理路径含该串的文件")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    base = ROOT / "assets"
    total_low = total_refused = 0
    n_files = 0
    rows = []
    for p in sorted(base.rglob("*.svg")):
        if args.filter and args.filter not in str(p.relative_to(ROOT)):
            continue
        text = p.read_text(encoding="utf-8")
        new, below, refused, _raised = process(text, fix=args.fix)
        if not below and not refused:
            continue
        n_files += 1
        total_low += len(below)
        total_refused += len(refused)
        rows.append({"file": str(p.relative_to(ROOT)), "below": len(below),
                     "refused": [{"fs": f, "floor": fl, "text": t} for f, fl, t in refused]})
        if args.fix and new != text:
            p.write_text(new, encoding="utf-8")
    print(f"低于下限文字 {total_low} 处，涉及 {n_files} 个文件；"
          f"{'修复后仍需人工' if args.fix else '可安全放大之外'}拒绝 {total_refused} 处")
    if args.json:
        op = (ROOT / args.json).resolve()
        if not op.is_relative_to(ROOT):
            raise ValueError(f"--json 只允许写在仓库内: {args.json}")
        op.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print("报告:", op.relative_to(ROOT))
    return 1 if total_low else 0


if __name__ == "__main__":
    sys.exit(main())
