#!/usr/bin/env python3
"""英文文本变体派生（新结构版）：为所有含中文渲染文本的素材生成 `.en.svg`。

规则：
  * 可见 `<text>` 内容按 tools/en_variant_dict_full.json 精确匹配替换（人工级译名）；
  * `<title>`/`<desc>` 保留 "zh / En" 双语的英文半边；
  * 生成的 .en.svg 统一英文字体链（Inter,Helvetica,Arial,sans-serif）；
  * 生成后自动跑字号放大 + 标签重叠消解（与 P3 相同的几何口径），保证不溢出不重叠；
  * `--strict`：存在残留中文渲染文本或未翻译串 → 退出码 1。

用法：
  python3 tools/derive_en_variants.py            # 生成/刷新全部 .en.svg
  python3 tools/derive_en_variants.py --check    # 只报告未翻译/未生成
  python3 tools/derive_en_variants.py --strict   # 校验并作为门禁
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import fix_label_overlap as flo  # noqa: E402
import legibility as leg  # noqa: E402
import fix_labels_manual as flm  # noqa: E402

DICT = ROOT / "tools/en_variant_dict_full.json"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
TEXT_BLOCK = re.compile(r"(<text\b[^>]*>)(.*?)(</text>)", re.S)
TITLE_RE = re.compile(r"(<title\b[^>]*>)(.*?)(</title>)", re.S)
DESC_RE = re.compile(r"(<desc\b[^>]*>)(.*?)(</desc>)", re.S)
EN_CHAIN = "Inter,Helvetica,Arial,sans-serif"
FF_RE = re.compile(r'font-family="[^"]*"')


def load_dict() -> dict:
    return json.loads(DICT.read_text(encoding="utf-8"))


def zh_text_blocks(raw: str):
    out = []
    for m in TEXT_BLOCK.finditer(raw):
        inner = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if CJK.search(inner):
            out.append((m, inner))
    return out


def translate(raw: str, d: dict):
    """返回 (new_raw, untranslated:list)。"""
    untranslated = []
    parts = []
    last = 0
    for m, inner in zh_text_blocks(raw):
        en = d.get(inner)
        if not en:
            untranslated.append(inner)
            continue
        parts.append(raw[last:m.start()])
        tag = m.group(0)
        new_inner = re.sub(r"<[^>]+>", "", m.group(2))
        tag = tag.replace(new_inner, en, 1) if new_inner else tag
        # 属性内替换（如 <tspan x="1">每</tspan> 逐字块的罕见情形不做拆分，走未翻译路径）
        parts.append(tag)
        last = m.end()
    parts.append(raw[last:])
    return "".join(parts), untranslated


def en_meta(raw: str) -> str:
    """title/desc 保留英文半边。"""
    def half(m):
        content = m.group(2)
        if "/" in content:
            content = content.split("/", 1)[1].strip()
        return m.group(1) + content + m.group(3)
    raw = TITLE_RE.sub(half, raw)
    raw = DESC_RE.sub(half, raw)
    raw = FF_RE.sub(f'font-family="{EN_CHAIN}"', raw)
    return raw


def _vb(raw: str):
    m = re.search(r'viewBox="([^"]+)"', raw)
    if not m:
        return None
    vals = [float(v) for v in m.group(1).replace(",", " ").split()]
    return vals[0], vals[1], vals[2], vals[3]


def reflow_en(raw: str) -> str:
    """英文标签出画修复：先降到字号下限，仍溢出则按词换行（拆成多枚 <text>）。"""
    vb = _vb(raw)
    if not vb:
        return raw
    _vx, _vy, vw, vh = vb
    floor = leg.floor_for(max(vw, vh))
    out = raw

    def fix_block(m):
        tag = m.group(0)
        a = dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]))
        if "font-size" not in a:
            return tag
        fs = float(a["font-size"])
        content = re.sub(r"<[^>]+>", "", tag)
        anchor = a.get("text-anchor", "start")
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        use = fs
        w = leg.measure(content, use)
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor in ("end", "right") else x)
        allowed = vw - 1.0
        if x0 + w <= vw - 0.5 and x0 >= 0.5:
            return tag  # 不溢出
        # 1) 先降到下限
        if use > floor:
            use = floor
            w = leg.measure(content, use)
            x0 = x - w / 2 if anchor == "middle" else (x - w if anchor in ("end", "right") else x)
        if x0 + w <= vw - 0.5 and x0 >= 0.5:
            return tag.replace(f'font-size="{leg.a_num(fs)}"', f'font-size="{leg.a_num(use)}"', 1)
        # 2) 换行：按词切分为若干行，行宽 ≤ allowed
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
        if any(leg.measure(ln, use) > allowed for ln in lines):
            return tag  # 单词过长等罕见情形，留闸门报
        # 以首行为基准重建：剥离旧 x/y/font-size，逐行重建干净的 <text>
        open_tag = tag[: tag.index(">")]  # 不含 '>'
        open_tag = re.sub(r'\s+(x|y|font-size)="[^"]*"', "", open_tag)
        open_tag += f' font-size="{leg.a_num(use)}"'
        pieces = []
        dy0 = 0.0 if y - use * 0.8 >= 0.5 else (0.5 + use * 0.8 - y)
        for i, ln in enumerate(lines):
            lw = leg.measure(ln, use)
            lx = x - lw / 2 if anchor == "middle" else (x - lw if anchor in ("end", "right") else x)
            ly = y + i * use * 1.18 + dy0
            pieces.append(f'{open_tag} x="{round(lx, 2)}" y="{round(ly, 2)}">{ln}</text>')
        return "".join(pieces)

    prev = None
    for _pass in range(3):  # 硬上限：正常 1 轮收敛，2 轮复核
        prev = out
        out = TEXT_BLOCK.sub(fix_block, out)
        if out == prev:
            break
    return out


def find_zh_files():
    files = []
    for p in sorted((ROOT / "assets").rglob("*.svg")):
        if p.name.endswith(".en.svg"):
            continue
        raw = p.read_text(encoding="utf-8")
        if zh_text_blocks(raw):
            files.append(p)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="英文文本变体派生 / 校验")
    ap.add_argument("--check", action="store_true", help="只报告不落盘")
    ap.add_argument("--strict", action="store_true", help="有未翻译串或残留中文 → 退出码 1")
    args = ap.parse_args(argv)

    d = load_dict()
    zh_files = find_zh_files()
    untranslated = {}
    generated = 0
    for p in zh_files:
        raw = p.read_text(encoding="utf-8")
        new_raw, un = translate(raw, d)
        if un:
            untranslated[str(p.relative_to(ROOT))] = un
        if args.check or args.strict:
            continue  # 校验模式不落盘
        en_path = p.with_name(p.stem + ".en.svg")
        en_raw = reflow_en(en_meta(new_raw))
        en_path.write_text(en_raw, encoding="utf-8")
        # 自动保证英文版同样满足字号/重叠口径
        flm.process_file(en_path, fix=True)
        flm.overlap_fix_pass(en_path)
        generated += 1
        if generated % 50 == 0:
            print(f"    …已生成 {generated}/{len(zh_files)}", flush=True)

    print(f"含中文渲染文本素材 {len(zh_files)} 个；生成 .en.svg {generated} 个；"
          f"未翻译串文件 {len(untranslated)} 个")
    if untranslated:
        for f, u in list(untranslated.items())[:20]:
            print("  UNTRANSLATED", f, u[:3])
    if args.check or args.strict:
        # 中文原版保留中文是预期行为；门禁口径是：
        #  (a) 每个含中文渲染文本的素材都有同名 .en.svg；
        #  (b) 所有 .en.svg 不含中文渲染文本（全量扫描，含未在本次清单内的）。
        missing_pairs = []
        leftover_cjk = []
        for p in sorted((ROOT / "assets").rglob("*.svg")):
            raw = p.read_text(encoding="utf-8")
            has_zh = bool(zh_text_blocks(raw))
            if p.name.endswith(".en.svg"):
                if has_zh:
                    leftover_cjk.append(str(p.relative_to(ROOT)))
            elif has_zh:
                en_path = p.with_name(p.stem + ".en.svg")
                if not en_path.exists():
                    missing_pairs.append(str(p.relative_to(ROOT)))
        n_en = len(list((ROOT / "assets").rglob("*.en.svg")))
        print(f"复查：.en.svg 共 {n_en} 个；缺配对 {len(missing_pairs)}；"
              f".en 残留中文 {len(leftover_cjk)}")
        if missing_pairs[:10]:
            print("  MISSING", missing_pairs[:10])
        if leftover_cjk[:10]:
            print("  LEFTOVER", leftover_cjk[:10])
        if args.strict and (untranslated or missing_pairs or leftover_cjk):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
