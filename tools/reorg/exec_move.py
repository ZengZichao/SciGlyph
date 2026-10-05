# -*- coding: utf-8 -*-
"""P2 执行器：按 move-map.json 执行 git mv 重命名迁移 + D 库许可归一 + 新 manifest 生成。

用法：
  python3 tools/reorg/exec_move.py --dry    # 只演练，不落盘
  python3 tools/reorg/exec_move.py          # 执行
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping import CATEGORIES, SUBDIRS

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "tools/reorg/move-map.json"

LICENSE = "CC-BY-4.0"
LICENSE_URI = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = "ZengZichao (https://github.com/ZengZichao)"

CAT_ZH = {c[0]: c[2] for c in CATEGORIES}
CAT_EN = {c[0]: c[3] for c in CATEGORIES}
SUB_ZH = {k: v[2] for k, v in SUBDIRS.items()}
SUB_EN = {k: v[3] for k, v in SUBDIRS.items()}

VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def augment_tags(row):
    """保证 tags ≥ 3：并入 en 名词元、slug 词元、中文名。"""
    tags = []
    seen = set()

    def add(t):
        t = str(t).strip().lower()
        if t and t not in seen:
            seen.add(t)
            tags.append(t)

    for t in row.get("tags") or []:
        add(t)
    add(row.get("name_zh"))
    add((row.get("name_en") or "").lower())
    for w in re.split(r"[^a-z0-9]+", (row.get("name_en") or "").lower()):
        if len(w) >= 3:
            add(w)
    for w in row.get("slug0", "").split("-"):
        if len(w) >= 3:
            add(w)
    if len(tags) < 3:
        add(row["subdir"].replace("-", " "))
    return tags[:10]


def read_canvas(p: Path) -> str:
    if p.exists():
        head = p.read_bytes()[:2048].decode("utf-8", "ignore")
        m = VIEWBOX_RE.search(head)
        if m:
            return m.group(1)
    return ""


def title_en(s: str) -> str:
    return " ".join(w.capitalize() if w.islower() else w for w in s.split())


def fix_names(row):
    zh = (row.get("name_zh") or "").strip()
    en = (row.get("name_en") or "").strip()
    if not en:
        en = title_en(row["slug0"].replace("-", " "))
    if not zh:
        zh = en
    return zh, en


def item_entry(row, base: Path) -> dict:
    zh, en = fix_names(row)
    return OrderedDict([
        ("file", f"{row['nnn']}-{row['slug']}.svg"),
        ("name_zh", zh),
        ("name_en", en),
        ("tags", augment_tags(row)),
        ("series", row["series"]),
        ("format", row["format"]),
        ("category", row["cat_dir"]),
        ("subdir", row["subdir"]),
        ("canvas", row.get("canvas") or read_canvas(base / row["dst"])),
        ("desc", (row.get("desc") or "").strip()),
        ("license", LICENSE),
        ("license_uri", LICENSE_URI),
        ("attribution", ATTRIBUTION),
    ])


def write_manifests(rows):
    assets = ROOT / "assets"
    top = OrderedDict([
        ("name", "科研绘图素材库"),
        ("name_en", "Scientific Illustration Asset Library"),
        ("version", "1.0.0"),
        ("license", LICENSE),
        ("license_uri", LICENSE_URI),
        ("attribution", ATTRIBUTION),
        ("credit_line", "Assets CC BY 4.0 · tools & pages MIT · (c) ZengZichao"),
        ("total", len(rows)),
        ("series_legend", {
            "classic": "经典科研插画（原子库A）", "atlas": "微生物图谱（原子库B）",
            "icon24": "24×24 线性图标（原子库C）", "primitives": "科研通用图元（原子库D）",
            "labflow": "实验室流程与设备（原子库E）"}),
        ("format_legend", {"illustration": "插画", "diagram": "示意图表", "icon": "24×24 线性图标（currentColor）"}),
        ("categories", []),
    ])
    by_cat = OrderedDict()
    for r in rows:
        by_cat.setdefault(r["cat_dir"], []).append(r)
    for cat_dir, rs in by_cat.items():
        no = cat_dir.split("-")[0]
        cat_entry = OrderedDict([
            ("id", cat_dir), ("name_zh", CAT_ZH[no]), ("name_en", CAT_EN[no]),
            ("count", len(rs)), ("subdirs", []),
        ])
        by_sub = OrderedDict()
        for r in rs:
            by_sub.setdefault(r["subdir"], []).append(r)
        items_all = []
        for sub, rs2 in by_sub.items():
            items = [item_entry(r, ROOT) for r in rs2]
            items_all.extend(items)
            man = OrderedDict([
                ("category", cat_dir),
                ("subdir", sub),
                ("name_zh", SUB_ZH[sub]),
                ("name_en", SUB_EN[sub]),
                ("count", len(items)),
                ("license", LICENSE),
                ("license_uri", LICENSE_URI),
                ("attribution", ATTRIBUTION),
                ("items", items),
            ])
            out = ROOT / "assets" / cat_dir / sub / "manifest.json"
            out.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            cat_entry["subdirs"].append(OrderedDict([
                ("id", sub), ("name_zh", SUB_ZH[sub]), ("name_en", SUB_EN[sub]), ("count", len(items)),
            ]))
        cdir = ROOT / "assets" / cat_dir
        cman = OrderedDict([
            ("category", cat_dir),
            ("name_zh", CAT_ZH[no]),
            ("name_en", CAT_EN[no]),
            ("count", len(items_all)),
            ("license", LICENSE),
            ("license_uri", LICENSE_URI),
            ("attribution", ATTRIBUTION),
            ("subdirs", cat_entry["subdirs"]),
        ])
        (cdir / "manifest.json").write_text(
            json.dumps(cman, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        top["categories"].append(cat_entry)
    (assets / "manifest.json").write_text(
        json.dumps(top, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--manifests-only", action="store_true",
                    help="只重新生成 manifest（素材已迁移完成时用）")
    args = ap.parse_args()

    rows = json.loads(MAP.read_text(encoding="utf-8"))
    assert len(rows) == 2830

    if args.manifests_only:
        for r in rows:
            if not r.get("canvas"):
                r["canvas"] = read_canvas(ROOT / r["dst"])
        write_manifests(rows)
        print("manifest 已重新生成")
        return

    # 1) 预哈希
    print("[1/5] 预哈希源文件…")
    pre = {}
    for r in rows:
        pre[r["src"]] = sha256(ROOT / r["src"])

    # 2) 建目录 + git mv
    print("[2/5] git mv …")
    dst_dirs = set()
    for r in rows:
        dst_dirs.add(str((ROOT / r["dst"]).parent))
    for d in sorted(dst_dirs):
        os.makedirs(ROOT / d, exist_ok=True)
    n = 0
    for i, r in enumerate(rows):
        src, dst = ROOT / r["src"], ROOT / r["dst"]
        if dst.exists():
            n += 1
            continue
        if not args.dry:
            subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT, check=True,
                           capture_output=True)
        n += 1
        if (i + 1) % 500 == 0:
            print(f"    moved {i+1}/{len(rows)}")
    print(f"    git mv done: {n}")

    if args.dry:
        print("(dry run，未落盘)")
        return

    # 3) 哈希校验
    print("[3/5] 哈希校验…")
    bad = []
    for r in rows:
        if sha256(ROOT / r["dst"]) != pre[r["src"]]:
            bad.append(r["dst"])
    assert not bad, f"哈希不一致 {len(bad)}: {bad[:5]}"
    left = len(list((ROOT / "子库A/assets").rglob("*.svg"))) + \
        len(list((ROOT / "子库B/assets").rglob("*.svg"))) + \
        len(list((ROOT / "子库C/assets").rglob("*.svg"))) + \
        len(list((ROOT / "子库D/assets").rglob("*.svg"))) + \
        len(list((ROOT / "子库E/assets").rglob("*.svg")))
    print(f"    旧库剩余 SVG: {left}（应 0）")
    assert left == 0

    # 4) D 子库来源许可归一 CC0-1.0 -> CC-BY-4.0
    print("[4/5] 许可归一…")
    fixed = 0
    for r in rows:
        if r["sub"] != "D":
            continue
        p = ROOT / r["dst"]
        t = p.read_text(encoding="utf-8")
        if 'data-license="CC0-1.0"' in t:
            t = t.replace('data-license="CC0-1.0"', 'data-license="CC-BY-4.0"')
            p.write_text(t, encoding="utf-8")
            fixed += 1
    print(f"    data-license 归一: {fixed} 个文件")

    # 5) 生成新 manifest 体系
    print("[5/5] 生成 manifest…")
    for r in rows:
        if not r.get("canvas"):
            r["canvas"] = read_canvas(ROOT / r["dst"])
    write_manifests(rows)

    total = sum(1 for _ in (ROOT / "assets").rglob("*.svg"))
    print(f"    新 assets SVG 总数: {total}")
    print("P2 迁移完成")


if __name__ == "__main__":
    main()
