# -*- coding: utf-8 -*-
"""生成逐素材接触表（contact sheet）HTML，供浏览器整页截图后交 agent 视觉复核。

- 每张表 6 列 × 8 行 = 48 格，格子内 190px 图 + 文件名 + 中英文名 + 画布；
- 只引用 assets/ 下的原始 SVG（<img>，相对路径），不复制、不改写素材；
- 同时输出 qa/review/sheets-index.json：sheet -> [素材相对路径]，供分配复核任务。

用法：python tools/review/make_sheets.py [--cat 01-cells-microbes] [--per 48]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
SHEETS = ROOT / "qa" / "review" / "sheets"
COLS, ROWS = 8, 6

CSS = """
html,body{margin:0;padding:0;background:#fff;font-family:"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{padding:8px}
h1{font:600 15px/1.3 sans-serif;margin:2px 0 8px;color:#111}
.grid{display:grid;grid-template-columns:repeat(8,1fr);gap:4px}
.cell{border:1px solid #e3e3e3;background:#fff;padding:2px;box-sizing:border-box}
.dark .cell{background:#1f2428;border-color:#3a4248}
.dark{background:#15181b}
.imgbox{height:170px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.imgbox img{max-width:100%;max-height:170px;display:block}
.cap{font:9.5px/1.3 "Consolas","Courier New",monospace;color:#333;word-break:break-all}
.dark .cap{color:#c9d1d6}
.cap b{color:#0b6}
.zh{font:11px/1.25 "Microsoft YaHei",sans-serif;color:#111}
.dark .zh{color:#e6e6e6}
.tag{color:#a33}
.dark .tag{color:#f88}
"""


def names(sub: Path, stem: str):
    mp = sub / "manifest.json"
    if not mp.exists():
        return "", "", ""
    m = json.loads(mp.read_text(encoding="utf-8"))
    base = re.sub(r"\.en$", "", stem)
    for it in m.get("items", []):
        if it.get("file", "").startswith(base):
            en_file = it["file"][:-4] + ".en.svg"
            has_en = (sub / en_file).exists()
            return it.get("name_zh", ""), it.get("name_en", ""), ("+en" if has_en else "")
    return "", "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="")
    ap.add_argument("--per", type=int, default=COLS * ROWS)
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--sets", default="", help="wave2 集合 json：{set名: [素材路径]}")
    ap.add_argument("--prefix", default="s")
    ap.add_argument("--chunk", default="", help="每个集合的分页大小，如 redraw=15,clip=76")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("*.html"):
        old.unlink()
    index = []
    n = 0
    if args.sets:
        sets = json.loads((ROOT / args.sets).read_text(encoding="utf-8"))
        sizes = {}
        for kv in args.chunk.split(","):
            if "=" in kv:
                k, v = kv.split("=")
                sizes[k.strip()] = int(v)
        n = 0
        for name, paths in sets.items():
            per = sizes.get(name, args.per)
            for i in range(0, len(paths), per):
                n += 1
                chunk = paths[i:i + per]
                cells, rels = [], []
                for a in chunk:
                    f = ROOT / os.path.normpath(a)
                    rel = Path(os.path.relpath(f, SHEETS)).as_posix()
                    zh, en, x = names(f.parent, f.stem)
                    rels.append(a)
                    cells.append(
                        f'<div class="cell"><div class="imgbox"><img src="{rel}"></div>'
                        f'<div class="zh">{zh}</div><div class="cap">{f.name}</div>'
                        f'<div class="cap">{en}</div></div>')
                title = f"{name} part {i // per + 1} ({len(chunk)} assets)"
                html = (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
                        f'<title>{title}</title><style>{CSS}</style></head><body><div class="wrap">'
                        f'<h1>{title}</h1><div class="grid">' + "".join(cells) + "</div></div></body></html>")
                out = SHEETS / f"{args.prefix}{n:03d}.html"
                out.write_text(html, encoding="utf-8")
                index.append({"sheet": out.name, "title": title, "assets": rels})
        (ROOT / "qa" / "review" / "sheets-index.json").write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8")
        print(f"sheets={n} assets={sum(len(x['assets']) for x in index)}")
        return

    for sub in sorted(ASSETS.glob("*/*/")):
        if args.cat and not sub.parent.name.startswith(args.cat):
            continue
        svgs = sorted(p for p in sub.glob("*.svg") if not p.name.endswith(".en.svg"))
        en_only = [p for p in sub.glob("*.en.svg")]
        items = svgs + en_only
        page = 1
        for i in range(0, len(items), args.per):
            chunk = items[i:i + args.per]
            n += 1
            cells = []
            rels = []
            for f in chunk:
                rel = Path(os.path.relpath(f, SHEETS)).as_posix().replace("/","/")
                zh, en, x = names(sub, f.stem)
                rels.append(f.relative_to(ROOT).as_posix())
                cells.append(
                    f'<div class="cell"><div class="imgbox"><img src="{rel}" loading="eager"></div>'
                    f'<div class="zh">{zh} <span class="tag">{x}</span></div>'
                    f'<div class="cap">{f.name}<b>{"" if zh else " [no-name]"}</b></div>'
                    f'<div class="cap">{en}</div></div>'
                )
            title = f"{sub.parent.name}/{sub.name} page {page}"
            html = (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
                    f'<title>{title}</title><style>{CSS}</style></head>'
                    f'<body class="{"dark" if args.dark else ""}"><div class="wrap">'
                    f'<h1>{title} · {len(chunk)} assets</h1><div class="grid">'
                    + "".join(cells) + "</div></div></body></html>")
            out = SHEETS / f"s{n:03d}.html"
            out.write_text(html, encoding="utf-8")
            index.append({"sheet": out.name, "title": title, "assets": rels})
            page += 1
    (ROOT / "qa" / "review" / "sheets-index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"sheets={n} assets={sum(len(x['assets']) for x in index)}")


if __name__ == "__main__":
    main()
