#!/usr/bin/env python3
"""新结构唯一总闸门：结构 / 命名 / manifest 严格字段 / SVG 安全 / 许可元数据 /
CJK 字体链 / 字号下限 / 标签零重叠 / 安全标志对称。

用法：
  python3 tools/check_repo.py            # 全部闸门
  python3 tools/check_repo.py --list     # 附带结构统计
退出码：0 全绿；1 有失败项（逐条列出）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "review"))

from svgtext import has_cjk_text, safe_fromstring, xml_guard  # noqa: E402
import check_symbol_symmetry as symmetry  # noqa: E402
import fix_label_overlap  # noqa: E402
import legibility  # noqa: E402
import scan_structure  # noqa: E402

ASSETS = ROOT / "assets"
NAME_RE = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.svg$")
EN_RE = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.en\.svg$")
CAT_DIR_RE = re.compile(r"^\d{2}-[a-z0-9-]+$")
CJK_FALLBACKS = ("PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC",
                 "Heiti SC", "SimHei", "WenQuanYi", "Source Han Sans")
COLOR_VAL_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|none|currentColor)$")
REQUIRED_ITEM_FIELDS = ("file", "name_zh", "name_en", "tags", "series", "format",
                        "category", "canvas", "license", "license_uri", "attribution")
SERIES_OK = {"classic", "atlas", "icon24", "primitives", "labflow"}
FORMAT_OK = {"illustration", "diagram", "icon"}
CJK_IN_EN = re.compile(r"[㐀-鿿豈-﫿]")
EDIT_RESIDUE = re.compile(r"同上|变体同步|已同步|请主控|待主控|需人工|作废|二选一|未落盘|待重画|理由[:：]|※|`")


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def check_structure(fails):
    cats = sorted(d.name for d in ASSETS.iterdir() if d.is_dir())
    expect = sorted(c["id"] for c in load_json(ASSETS / "manifest.json")["categories"])
    if cats != expect:
        fails.append(f"结构: 大类目录 {cats} != manifest 声明 {expect}")
    return cats


def check_naming(fails):
    names = Counter()
    for cat in sorted(ASSETS.iterdir()):
        if not cat.is_dir():
            if cat.name != "manifest.json":
                fails.append(f"结构: assets 下出现非目录 {cat.name}")
            continue
        if not CAT_DIR_RE.match(cat.name):
            fails.append(f"命名: 大类目录名不合规 {cat.name}")
        subdirs = [d for d in cat.iterdir() if d.is_dir()]
        # 映射表为最高依据（如 12-icons-ui 仅 1 个子目录、03 仅 2 个），上限 12
        if not 1 <= len(subdirs) <= 12:
            fails.append(f"结构: {cat.name} 二级目录数 {len(subdirs)} 不在 1~12")
        for sub in subdirs:
            if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", sub.name):
                fails.append(f"命名: 二级目录名不合规 {cat.name}/{sub.name}")
            nums = []
            for f in sub.iterdir():
                if f.is_dir():
                    fails.append(f"结构: 二级目录下出现子目录 {f}")
                    continue
                if f.name == "manifest.json":
                    continue
                if not (NAME_RE.match(f.name) or EN_RE.match(f.name)):
                    fails.append(f"命名: 文件名不合规 {f.relative_to(ASSETS)}")
                    continue
                names[f.name] += 1
                m = re.match(r"^(\d{3})-", f.name)
                if m:
                    nums.append(int(m.group(1)))
            if nums:
                want = list(range(1, len(set(nums)) + 1))
                if sorted(set(nums)) != want:
                    fails.append(f"编号: {cat.name}/{sub.name} 序号不连续或重复")
    for n, c in names.items():
        if c > 1:
            fails.append(f"命名: 文件名全库重复 {n}")
    return sum(names.values())


def check_svg_safety(fails):
    """零脚本 / 零外链 / 零位图 / 字面 hex / 许可元数据 / 字体链 / 字号 / 重叠 / zh-en 配对。"""
    n_svg = n_en = 0
    zh_with_text = set()
    en_files = set()
    for p in sorted(ASSETS.rglob("*.svg")):
        rel = str(p.relative_to(ROOT))
        n_svg += 1
        if p.name.endswith(".en.svg"):
            n_en += 1
            en_files.add(str(p.relative_to(ASSETS)))
        raw = p.read_text(encoding="utf-8")
        g = xml_guard(raw)
        if g:
            fails.append(f"SVG 安全 {rel}: {g}")
        low = raw.lower()
        if "<script" in low or "javascript:" in low:
            fails.append(f"SVG 安全 {rel}: 含脚本")
        if "<image" in low or "data:image" in low:
            fails.append(f"SVG 安全 {rel}: 含内嵌位图")
        for m in re.finditer(r'(?:xlink:href|href)="(.*?)"', raw):
            v = m.group(1)
            if v.startswith(("http://", "https://", "//")):
                fails.append(f"SVG 安全 {rel}: 外链 {v[:60]}")
        if "<style" in low or "var(" in low or "calc(" in low:
            fails.append(f"SVG 安全 {rel}: 含 <style>/var()/calc()")
        for mu in re.finditer(r"url\(([^)]*)\)", raw):
            if not mu.group(1).strip().startswith("#"):
                fails.append(f"SVG 安全 {rel}: 非内部 url() 引用 {mu.group(0)[:40]}")
        for attr in ("fill", "stroke", "stop-color", "flood-color"):
            for m in re.finditer(rf'(?<![\w-]){attr}="([^"]*)"', raw):
                v = m.group(1).strip()
                if not v:
                    continue
                mu = re.fullmatch(r"url\(#([\w.-]+)\)", v)
                if mu:
                    # 内部图案/渐变引用：其组成颜色已由本循环的字面 hex 检查覆盖
                    if f'id="{mu.group(1)}"' not in raw:
                        fails.append(f"SVG 安全 {rel}: url 引用悬空 #{mu.group(1)}")
                elif not COLOR_VAL_RE.match(v):
                    fails.append(f"SVG 安全 {rel}: 非字面颜色 {attr}={v!r}")
        if 'data-license="CC-BY-4.0"' not in raw:
            fails.append(f"许可 {rel}: 缺 data-license=CC-BY-4.0")
        if 'data-copyright="ZengZichao"' not in raw:
            fails.append(f"许可 {rel}: 缺 data-copyright=ZengZichao")
        try:
            tree = safe_fromstring(raw)
        except Exception as e:  # noqa: BLE001
            fails.append(f"SVG 解析 {rel}: {e}")
            continue
        if has_cjk_text(tree):
            zh_with_text.add(str(p.relative_to(ASSETS)))
            ok = any(any(c in ff.get("font-family") for c in CJK_FALLBACKS)
                     for ff in tree.iter() if ff.get("font-family"))
            if not ok:
                fails.append(f"字体链 {rel}: 渲染 CJK 文本但 font-family 无 CJK 回退族")
        _new, below, _refused, _raised = legibility.process(raw, fix=False)
        for f in below:
            fails.append(f"字号 {rel}: {f[0]} < 下限 {f[1]} ({f[2]!r})")
        info = fix_label_overlap.analyze(raw)
        if info:
            pairs, boxes, vw, vh = info
            for i, j in pairs:
                fails.append(f"标签重叠 {rel}: {boxes[i][0][:16]!r} × {boxes[j][0][:16]!r}")
            if vw is not None:
                for content, _el, box, _m, _fs in boxes:
                    if box[0] < -0.5 or box[1] < -0.5 or box[2] > vw + 0.5 or box[3] > vh + 0.5:
                        fails.append(f"文字出画 {rel}: {content[:20]!r} "
                                     f"box x[{box[0]:.0f}..{box[2]:.0f}] y[{box[1]:.0f}..{box[3]:.0f}] "
                                     f"viewBox {vw:g}×{vh:g}")
    # zh/en 配对完整性：中文渲染素材必须有 .en 兄弟；.en 必须有中文母本且自身无 CJK
    for rel in sorted(zh_with_text):
        en_rel = rel.replace(".svg", ".en.svg")
        if en_rel not in en_files:
            fails.append(f"zh-en 配对 {rel}: 缺 {en_rel}")
    for rel in sorted(en_files):
        zh_rel = rel.replace(".en.svg", ".svg")
        if not (ASSETS / zh_rel).exists():
            fails.append(f"zh-en 配对 {rel}: 母本 {zh_rel} 不存在")
    return n_svg, n_en


def check_manifests(fails):
    top = load_json(ASSETS / "manifest.json")
    for k in ("license", "license_uri", "attribution", "total"):
        if not top.get(k):
            fails.append(f"manifest: 顶层缺 {k}")
    manifest_files = set()
    en_refs = set()
    n_items = 0
    for catman in top["categories"]:
        cdir = ASSETS / catman["id"]
        cm = load_json(cdir / "manifest.json")
        ndisk = len([p for p in cdir.rglob("*.svg") if not p.name.endswith(".en.svg")])
        if cm.get("count") != ndisk:
            fails.append(f"manifest: {catman['id']} count {cm.get('count')} 与磁盘主素材 {ndisk} 不符")
        for sub in cm["subdirs"]:
            sm = load_json(cdir / sub["id"] / "manifest.json")
            for it in sm["items"]:
                n_items += 1
                for k in REQUIRED_ITEM_FIELDS:
                    v = it.get(k)
                    if v is None or v == "" or (k == "tags" and len(v) < 3):
                        fails.append(
                            f"manifest: {sm['category']}/{sm['subdir']}/{it.get('file')} 字段 {k} 缺失或不足")
                if it.get("series") not in SERIES_OK:
                    fails.append(f"manifest: 非法 series {it.get('series')}")
                if it.get("format") not in FORMAT_OK:
                    fails.append(f"manifest: 非法 format {it.get('format')}")
                for fld in ("name_zh", "name_en", "desc"):
                    val = it.get(fld, "") or ""
                    who = f"{sm['category']}/{sm['subdir']}/{it.get('file')}"
                    if fld == "name_en" and CJK_IN_EN.search(val):
                        fails.append(f"manifest: {who} 的 name_en 含非英文字符 {val[:40]!r}")
                    if fld != "name_en" and EDIT_RESIDUE.search(val):
                        fails.append(f"manifest: {who} 的 {fld} 含复核批注残留 {val[:40]!r}")
                    if fld == "name_zh" and re.search(r"\s->\s", val):
                        fails.append(f"manifest: {who} 的 name_zh 含未落盘的改名字段 {val[:40]!r}")
                fp = cdir / sub["id"] / it["file"]
                if not fp.exists():
                    fails.append(f"manifest: 条目文件不存在 {fp.relative_to(ASSETS)}")
                manifest_files.add(str(fp.relative_to(ASSETS)))
                if it.get("en"):
                    ep = cdir / sub["id"] / it["en"]
                    if not ep.exists():
                        fails.append(f"manifest: en 配对不存在 {ep.relative_to(ASSETS)}")
                    en_refs.add(str(ep.relative_to(ASSETS)))
    for p in ASSETS.rglob("*.svg"):
        rel = str(p.relative_to(ASSETS))
        if rel in manifest_files or rel in en_refs:
            continue
        if p.name.endswith(".en.svg"):
            fails.append(f"manifest: en 变体未登记 {rel}")
        else:
            fails.append(f"manifest: 素材未登记 {rel}")
    return n_items


def check_symmetry(fails):
    targets = symmetry.DEFAULT_TARGETS
    if not targets:
        fails.append("对称校验: 未找到辐射三叶/生物危害标志")
        return
    nfail = 0
    for rel in targets:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"对称校验: 目标不存在 {rel}")
            nfail += 1
            continue
        ok, msg = symmetry.check(p, 3, 0.25)
        print(f"      [{'PASS' if ok else 'FAIL'}] {rel}: {msg}")
        if ok is False:
            nfail += 1
    if nfail:
        fails.append(f"安全标志旋转对称: {nfail} 项未过")


def _utf8_stdout():
    # Windows 控制台默认 GBK，闸门输出里的 ✓ / 中文会抛 UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def check_renderable(fails):
    """图元是否真的会被渲染：xmlns / 属性错配 / 零面积不可见 / 宽高比与 viewBox 失配。"""
    n = 0
    for f in sorted(ASSETS.glob("*/*/*.svg")):
        n += 1
        issues, _ = scan_structure.scan(f)
        rel = f.relative_to(ROOT).as_posix()
        for i in issues:
            fails.append(f"可渲染性 {rel}: {i}")
    return n


def main(argv=None):
    _utf8_stdout()
    ap = argparse.ArgumentParser(description="新结构总闸门")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    fails = []
    cats = check_structure(fails)
    n_named = check_naming(fails)
    n_manifest = check_manifests(fails)
    n_svg, n_en = check_svg_safety(fails)
    check_symmetry(fails)

    n_struct = check_renderable(fails)

    print("=" * 62)
    print(f"大类 {len(cats)} · 命名扫描 {n_named} · SVG {n_svg}（.en.svg {n_en}）· manifest 条目 {n_manifest}")
    if args.list:
        for cat in cats:
            subs = sorted(d.name for d in (ASSETS / cat).iterdir() if d.is_dir())
            n = len(list((ASSETS / cat).rglob("*.svg")))
            print(f"  {cat}: {n} 素材 · {len(subs)} 子目录")
    if fails:
        uniq = Counter(fails)
        print(f"\n未通过 {len(fails)} 项（去重 {len(uniq)} 类）：")
        for f, c in uniq.most_common(60):
            print("  ✗", f"{f} ×{c}" if c > 1 else f)
        if len(uniq) > 60:
            print(f"  …另有 {len(uniq) - 60} 类，略")
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
