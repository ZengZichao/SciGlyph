# -*- coding: utf-8 -*-
"""用无头 Edge 把 qa/review/sheets/*.html 逐页截成 PNG（接触表截图）。

高度按该页格子数推算，避免整页截断；输出 qa/review/png/sNNN.png。
用法：python tools/review/render_sheets.py [--only s001 s005] [--overwrite]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / "qa" / "review" / "sheets"
PNG = ROOT / "qa" / "review" / "png"
COLS = 8
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def browser():
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("未找到 Edge/Chrome 可执行文件")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    PNG.mkdir(parents=True, exist_ok=True)
    idx = {x["sheet"]: len(x["assets"]) for x in
           json.loads((ROOT / "qa" / "review" / "sheets-index.json").read_text(encoding="utf-8"))}
    exe = browser()
    done = skipped = failed = 0
    for html in sorted(SHEETS.glob("*.html")):
        if args.only and html.stem not in args.only:
            continue
        out = PNG / (html.stem + ".png")
        if out.exists() and not args.overwrite:
            skipped += 1
            continue
        rows = -(-idx.get(html.name, 48) // COLS)
        h = rows * 252 + 70
        with tempfile.TemporaryDirectory(prefix="edgeqa") as udd:
            cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                   f"--user-data-dir={udd}", "--force-device-scale-factor=1",
                   f"--window-size=1560,{h}", "--virtual-time-budget=8000",
                   f"--screenshot={out}", html.as_uri()]
            r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=180)
        if out.exists() and out.stat().st_size > 5000:
            done += 1
        else:
            failed += 1
            print("FAIL", html.name, (r.stderr or "")[-200:])
    print(f"截图完成 {done}，跳过 {skipped}，失败 {failed} -> {PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
