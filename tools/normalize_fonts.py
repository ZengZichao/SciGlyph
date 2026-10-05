#!/usr/bin/env python3
"""字体链归一：把全库 font-family 统一为两条规范链。

含 CJK 渲染文本 → 'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif
纯拉丁文本   → Inter,Helvetica,Arial,sans-serif

只改 font-family 属性；缺 font-family 的 <text> 会补上。幂等。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZH_CHAIN = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif"
EN_CHAIN = "Inter,Helvetica,Arial,sans-serif"
FF_RE = re.compile(r'font-family="[^"]*"')
TEXT_BLOCK_RE = re.compile(r"<text\b[^>]*>.*?</text>|<text\b[^>]*/>", re.S)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def rendered_text_has_cjk(text: str) -> bool:
    for m in TEXT_BLOCK_RE.finditer(text):
        block = m.group(0)
        inner = re.sub(r"<[^>]+>", "", block)
        if CJK.search(inner):
            return True
    return False


def normalize_file(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    chain = ZH_CHAIN if rendered_text_has_cjk(text) else EN_CHAIN
    orig = text
    text = FF_RE.sub(f'font-family="{chain}"', text)

    def fix_text_block(m):
        block = m.group(0)
        if "font-family" not in block:
            block = block.replace("<text", f'<text font-family="{chain}"', 1)
        return block

    text = TEXT_BLOCK_RE.sub(fix_text_block, text)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    n = 0
    files = 0
    for p in sorted((ROOT / "assets").rglob("*.svg")):
        files += 1
        if normalize_file(p):
            n += 1
    print(f"扫描 {files} 个 SVG，归一 font-family {n} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
