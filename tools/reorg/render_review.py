# -*- coding: utf-8 -*-
"""P3b：全量逐文件渲染 + 按二级目录生成接触表（contact sheets）。

- 每个素材渲染为 PNG（最长边 320px）到 qa/render/thumbs/<大类>/<子目录>/；
- currentColor 一律以 #333 渲染、白色底（仅渲染副本，不改源文件）；
- 每张接触表 8 列 × ≤6 行，格下标注文件名（去 .svg）；
- 渲染失败清单写入 qa/render/render-failures.json。

用法：python3 tools/reorg/render_review.py [--cat 01-cells-microbes]
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

THUMB = 320
COLS, ROWS, CELL = 8, 6, 156

import cairosvg  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def render_svg(src: Path, dst: Path) -> bool:
    try:
        raw = src.read_text(encoding="utf-8")
        if "currentColor" in raw:
            raw = raw.replace("currentColor", "#333333")
            tmp = Path(tempfile.mkstemp(suffix=".svg")[1])
            tmp.write_text(raw, encoding="utf-8")
            src_use = tmp
        else:
            src_use = src
        png = cairosvg.svg2png(url=str(src_use), output_width=THUMB, output_height=THUMB,
                               background_color="#FFFFFF")
        dst.write_bytes(png)
        if src_use != src:
            src_use.unlink()
        return True
    except Exception:  # noqa: BLE001
        try:
            if src_use != src:
                src_use.unlink()
        except Exception:  # noqa: BLE001
            pass
        return False


def font():
    for name in ("/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Menlo.ttc"):
        if os.path.exists(name):
            try:
                return ImageFont.truetype(name, 11)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def sheet(items, out: Path, title: str):
    """items: [(label, png_path)]"""
    W = COLS * CELL + 8
    H = ROWS * (CELL + 16) + 26
    im = Image.new("RGB", (W, H), "#FFFFFF")
    dr = ImageDraw.Draw(im)
    dr.text((6, 5), title, fill="#111111", font=font())
    for idx, (label, png) in enumerate(items):
        r, c = divmod(idx, COLS)
        x, y = 4 + c * CELL, 24 + r * (CELL + 16)
        try:
            thumb = Image.open(png)
            thumb.thumbnail((CELL - 6, CELL - 6))
            im.paste(thumb, (x + (CELL - thumb.width) // 2, y + (CELL - thumb.height) // 2))
        except Exception:  # noqa: BLE001
            dr.rectangle((x, y, x + CELL - 6, y + CELL - 6), outline="#CC0000", width=2)
            dr.text((x + 8, y + CELL // 2), "RENDER FAIL", fill="#CC0000", font=font())
        dr.rectangle((x, y, x + CELL - 6, y + CELL - 6), outline="#DDDDDD", width=1)
        dr.text((x + 2, y + CELL - 2), label[:24], fill="#333333", font=font())
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="")
    args = ap.parse_args()

    assets = ROOT / "assets"
    thumbs = ROOT / "qa/render/thumbs"
    sheets = ROOT / "qa/render/sheets"
    failures = []
    n_ok = 0
    for cat in sorted(p for p in assets.iterdir() if p.is_dir()):
        if args.cat and not cat.name.startswith(args.cat):
            continue
        for sub in sorted(p for p in cat.iterdir() if p.is_dir()):
            svgs = sorted(sub.glob("*.svg"))
            tdir = thumbs / cat.name / sub.name
            tdir.mkdir(parents=True, exist_ok=True)
            tiles = []
            page = 1
            for f in svgs:
                tp = tdir / (f.stem + ".png")
                if not tp.exists():
                    if not render_svg(f, tp):
                        failures.append(str(f.relative_to(ROOT)))
                        tp.parent.mkdir(parents=True, exist_ok=True)
                        tp.write_bytes(b"")
                if tp.exists() and tp.stat().st_size:
                    n_ok += 1
                    tiles.append((f.stem, tp))
                else:
                    tiles.append((f.stem, None))
                if len(tiles) == COLS * ROWS:
                    sheet(tiles, sheets / f"{cat.name}__{sub.name}__p{page:02d}.png",
                          f"{cat.name}/{sub.name}  page {page}")
                    tiles = []
                    page += 1
            if tiles:
                sheet(tiles, sheets / f"{cat.name}__{sub.name}__p{page:02d}.png",
                      f"{cat.name}/{sub.name}  page {page}")
    (ROOT / "qa/render/render-failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"渲染成功 {n_ok}，失败 {len(failures)}；接触表目录 {sheets.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
