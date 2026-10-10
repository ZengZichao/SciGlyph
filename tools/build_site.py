# -*- coding: utf-8 -*-
"""把画廊站点装配到 site/（GitHub Pages 的发布产物，本地可同样用于预览）。

只收录访客需要的内容：index.html、assets/、preview/、许可与引用元数据；
工具与文档留在仓库但不发布。site/ 是可重建产物，不入库。

用法：python tools/build_site.py [--out site]
本地预览：python tools/build_site.py && python -m http.server -d site 8000
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLISH = ["index.html", "assets", "preview"]
PUBLISH_FILES = ["LICENSE", "LICENSE.md", "LICENSE-ASSETS", "NOTICE", "NOTICE.en.md",
                 "CITATION.cff", "README.md", "README.en.md",
                 "README-SERIES.md", "README-SERIES.en.md",
                 "CONTRIBUTING.md", "CONTRIBUTING.en.md"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    dst = ROOT / args.out
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n_svg = 0
    for name in PUBLISH:
        src = ROOT / name
        if not src.exists():
            print(f"[skip] 缺少 {name}")
            continue
        if src.is_dir():
            shutil.copytree(src, dst / name,
                            ignore=shutil.ignore_patterns("SPEC*.md", "__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst / name)
    for name in PUBLISH_FILES:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, dst / name)
    for p in dst.rglob("*.svg"):
        n_svg += 1
    (dst / ".nojekyll").write_text("", encoding="utf-8")
    size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    print(f"site/ 就绪：SVG {n_svg} 个，总大小 {size/1048576:.1f} MB")


if __name__ == "__main__":
    main()
