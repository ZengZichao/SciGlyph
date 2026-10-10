# -*- coding: utf-8 -*-
"""把 manifest 的名称/描述回灌到 SVG 的 <title> / <desc>，消除元数据漂移。

约定（与库内既有惯例一致）：
  - 中文素材 <title> = "name_zh / name_en"
  - .en 变体   <title> = name_en
  - <desc>     取 manifest 的 desc；.en 变体只取其中的英文部分（"关键词:" 之前），
               英文部分仍含 CJK 时保持原样不动（交人工）。
只改 <title>/<desc> 的文本节点，id、属性、图形一律不动。

用法：python tools/review/sync_svg_meta.py [--dry]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CJK = re.compile(r"[\u3400-\u9fff]")


def set_text(raw: str, tag: str, new: str):
    """替换 <tag ...>…</tag> 的文本，保留属性；无该标签则返回原串。"""
    pat = re.compile(r"(<" + tag + r"\b[^>]*>)(.*?)(</" + tag + r">)", re.S)
    m = pat.search(raw)
    if not m:
        return raw, False
    cur = m.group(2)
    if cur.strip() == new.strip():
        return raw, False
    esc = html.escape(new, quote=False)
    return raw[:m.start(2)] + esc + raw[m.end(2):], True


def en_desc(desc: str) -> str:
    head = re.split(r"关键词[:：]", desc)[0].strip()
    return head if head and not CJK.search(head) else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    n_title = n_desc = n_skip_desc = 0
    for mp in sorted((ROOT / "assets").glob("*/*/manifest.json")):
        data = json.loads(mp.read_text(encoding="utf-8"))
        dirty = {}
        for it in data.get("items", []):
            for fname in (it["file"], re.sub(r"\.svg$", ".en.svg", it["file"])):
                f = mp.parent / fname
                if not f.exists():
                    continue
                is_en = fname.endswith(".en.svg")
                exp_title = it["name_en"] if is_en else f'{it["name_zh"]} / {it["name_en"]}'
                raw = dirty.get(f) or f.read_text(encoding="utf-8")
                raw, c1 = set_text(raw, "title", exp_title)
                want = en_desc(it.get("desc", "")) if is_en else it.get("desc", "")
                if want:
                    raw, c2 = set_text(raw, "desc", want)
                else:
                    c2 = False
                    if is_en:
                        n_skip_desc += 1
                if is_en and not re.search(r"<desc\b", raw):
                    pass
                n_title += c1
                n_desc += c2
                if c1 or c2:
                    dirty[f] = raw
        for f, raw in dirty.items():
            if not args.dry:
                f.write_text(raw, encoding="utf-8", newline="")
    print(("DRY " if args.dry else "") + f"title 回灌 {n_title} 处，desc 回灌 {n_desc} 处，"
          f".en 无纯英文 desc 可回灌 {n_skip_desc} 处（保持原样）")


if __name__ == "__main__":
    main()
