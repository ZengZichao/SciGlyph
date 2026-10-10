# -*- coding: utf-8 -*-
"""画廊与素材的一致性闸门 + Pages 发布前的站点自检。

校验 index.html 内联的 DATA 与 assets/ 目录、manifest 一一对应，
并确认页面是自包含的（相对路径、零外链、零 fetch）：
  1. DATA 每条 f/en 指向的文件必须存在；
  2. assets/ 下每个 .svg（含 .en.svg）必须被 DATA 覆盖，且不重复；
  3. DATA 路径必须是相对路径（GitHub Pages 项目站点挂在 /<repo>/ 子路径下）；
  4. index.html 不得含 http(s) 外链、fetch/XHR、<script src>、内联事件外的远程资源；
  5. README 引用的 preview/*.png 必须存在；
  6. 不得存在以 _ 或 . 开头的、需要被站点服务的素材路径。

用法：python tools/check_site.py
退出码 0 全部通过；1 有失败项。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fails = []
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    i = html.find("const DATA=")
    if i < 0:
        print("[FAIL] index.html 中找不到 DATA 数组")
        return 1
    j = html.index("[", i)
    data, _ = json.JSONDecoder().raw_decode(html[j:])

    listed = set()
    for it in data:
        for key in ("f", "en"):
            v = it.get(key) or ""
            if not v:
                continue
            if v.startswith(("/", "http:", "https:", "\\")) or ".." in v:
                fails.append(f"非相对路径 {key}={v}")
            if v in listed:
                fails.append(f"DATA 重复条目 {v}")
            listed.add(v)
            if not (ROOT / v).exists():
                fails.append(f"DATA 指向缺失文件 {v}")

    on_disk = {str(p.relative_to(ROOT)).replace("\\", "/") for p in ASSETS.glob("*/*/*.svg")}
    missing = sorted(on_disk - listed)
    for v in missing:
        fails.append(f"素材未收录进画廊 {v}")
    ghost = sorted(p for p in listed - on_disk if p.endswith(".svg") and not p.endswith(".en.svg"))

    for pat, why in [(r"fetch\s*\(", "存在 fetch()，file:// 下会失败"),
                     (r"XMLHttpRequest", "存在 XHR"),
                     (r"<script[^>]+src=", "存在外部脚本"),
                     (r"(?:src|href)=[\"']https?://", "存在外链资源")]:
        if re.search(pat, html):
            fails.append(f"index.html {why}")

    for md in ("README.md", "README.en.md"):
        p = ROOT / md
        if not p.exists():
            fails.append(f"缺少 {md}")
            continue
        for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if img.startswith(("http:", "https:")):
                continue
            if not (ROOT / img).exists():
                fails.append(f"{md} 引用缺失图片 {img}")

    served = [p for p in ROOT.glob("assets/**") if p.name.startswith(("_", "."))]
    for p in served:
        fails.append(f"站点路径含下划线/点开头文件（Pages 会跳过）{p.relative_to(ROOT)}")

    print("=" * 62)
    print(f"DATA 条目 {len(data)} · 收录文件 {len(listed)} · 磁盘 SVG {len(on_disk)}")
    if fails:
        for f in fails[:60]:
            print("  ✗", f)
        print(f"失败 {len(fails)} 项")
        return 1
    print("站点自检 全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
