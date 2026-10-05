# -*- coding: utf-8 -*-
"""整合预览图生成：用 qa/render/thumbs 的缩略图拼合 4 张预览图到 preview/。

- preview/sciglyph-overview.png    全库总览（12 大类 × 8 张精选）
- preview/sciglyph-series.png      五个画风系列对比（每系列一行 12 张）
- preview/sciglyph-lab.png         实验室与安全（07/08/09 三类拼版）
- preview/sciglyph-figures.png     图表与图标（10/11/12 三类拼版）

确定性取样（按 manifest 顺序轮转），可重复生成。
用法：python3 tools/reorg/build_previews.py
依赖：qa/render/thumbs 缓存（python3 tools/reorg/render_review.py 先行生成）。
"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from gallery_theme import LIGHT  # noqa: E402

import cairosvg  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ASSETS = ROOT / "assets"
THUMBS = ROOT / "qa/render/thumbs"
OUT = ROOT / "preview"


def load_items():
    """[(category_dir, cat_zh, cat_en, subdir, file, series, thumb_path)]"""
    top = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    items = []
    for c in top["categories"]:
        cm = json.loads((ASSETS / c["id"] / "manifest.json").read_text(encoding="utf-8"))
        for s in cm["subdirs"]:
            sm = json.loads((ASSETS / c["id"] / s["id"] / "manifest.json").read_text(encoding="utf-8"))
            for it in sm["items"]:
                t = THUMBS / c["id"] / s["id"] / (it["file"][:-4] + ".png")
                items.append({"cat": c["id"], "cat_zh": c["name_zh"], "cat_en": c["name_en"],
                              "sub": s["id"], "file": it["file"], "series": it["series"],
                              "thumb": t, "name_zh": it["name_zh"], "name_en": it["name_en"]})
    return items


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ] + (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for name in candidates:
        if Path(name).exists():
            try:
                return ImageFont.truetype(name, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def grid_sheet(items, cols, tile, title, subtitle, out, pad=28):
    rows = (len(items) + cols - 1) // cols
    W = pad * 2 + cols * tile + (cols - 1) * 14
    H = pad + 52 + 26 + rows * tile + (rows - 1) * 14 + pad
    im = Image.new("RGB", (W, H), LIGHT["--bg"])
    dr = ImageDraw.Draw(im)
    dr.text((pad, pad), title, fill="#1B2733", font=font(30, bold=True))
    dr.text((pad, pad + 42), subtitle, fill="#5A6B7B", font=font(15))
    y0 = pad + 78
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (tile + 14)
        y = y0 + r * (tile + 14)
        dr.rounded_rectangle((x, y, x + tile, y + tile), 10, fill="#FFFFFF",
                             outline="#D9DEE4", width=1)
        t = it["thumb"]
        if t.exists():
            th = Image.open(t).convert("RGB")
            th.thumbnail((tile - 16, tile - 16))
            im.paste(th, (x + (tile - th.width) // 2, y + (tile - th.height) // 2))
        else:
            dr.text((x + 10, y + tile // 2), "thumb?", fill="#CC0000", font=font(12))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(out.relative_to(ROOT), f"{W}x{H}", f"{len(items)} tiles")


def pick(items, n, offset=0):
    step = max(1, len(items) // n)
    return [items[(offset + i * step) % len(items)] for i in range(n)]


def main():
    items = load_items()
    assert len(items) == 2830

    # 1) 全库总览：12 大类 × 8
    tiles = []
    for cat in OrderedDict.fromkeys(it["cat"] for it in items):
        cat_items = [it for it in items if it["cat"] == cat]
        tiles += pick(cat_items, 8)
    zh = "SciGlyph · 科研绘图 SVG 素材库 v1.0.0"
    en = "SciGlyph - Scientific Illustration Asset Library v1.0.0 (AI-generated, verify before use)"
    grid_sheet(tiles, 12, 150,
               zh + " / " + "2830 assets · CC BY 4.0",
               en, OUT / "sciglyph-overview.png")

    # 2) 系列对比：5 系列 × 12
    tiles = []
    for ser in ["classic", "atlas", "icon24", "primitives", "labflow"]:
        ser_items = [it for it in items if it["series"] == ser]
        tiles += pick(ser_items, 12)
    grid_sheet(tiles, 12, 128,
               "五个画风系列 / Five visual series: classic · atlas · icon24 · primitives · labflow",
               "Each row = one series, sampled across categories · AI-generated artwork, CC BY 4.0 (c) ZengZichao",
               OUT / "sciglyph-series.png")

    # 3) 实验室与安全：07/08/09 × 16
    tiles = []
    for cat in ["07-glassware-consumables", "08-instruments-apparatus", "09-safety-signage"]:
        cat_items = [it for it in items if it["cat"] == cat]
        tiles += pick(cat_items, 16)
    grid_sheet(tiles, 8, 160,
               "器皿·仪器·安全 / Glassware · Instruments · Safety signage",
               "Sampled from categories 07 / 08 / 09 · AI-generated, verify accuracy before use · CC BY 4.0",
               OUT / "sciglyph-lab.png")

    # 4) 图表与图标：10/11/12 × 16
    tiles = []
    for cat in ["10-figure-elements", "11-diagrams-charts", "12-icons-ui"]:
        cat_items = [it for it in items if it["cat"] == cat]
        tiles += pick(cat_items, 16)
    grid_sheet(tiles, 8, 160,
               "图版构件·图表·图标 / Figure elements · Charts · Icons",
               "Sampled from categories 10 / 11 / 12 · AI-generated, verify accuracy before use · CC BY 4.0",
               OUT / "sciglyph-figures.png")


if __name__ == "__main__":
    main()
