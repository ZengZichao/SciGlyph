# -*- coding: utf-8 -*-
"""P1：生成完整迁移映射 move-map.json、审查台账 qa/review-ledger.json 与 REORG-PLAN.md。

用法：python3 tools/reorg/build_map.py
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping import (CATEGORIES, SUBDIRS, WHOLE_MAP, SERIES, SPLIT_RULES)

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录
SUBS = {"A": "子库A", "B": "子库B", "C": "子库C", "D": "子库D", "E": "子库E"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


META = {}  # (sub, cat, fname) -> {name_zh, name_en, tags, desc, canvas}


def put(sub, cat, fname, **kw):
    META.setdefault((sub, cat, fname), {})
    META[(sub, cat, fname)].update(kw)


def load_meta():
    # A：categories[].items[]
    m = load_json(ROOT / "子库A/manifest.json")
    for c in m["categories"]:
        for it in c["items"]:
            put("A", c["id"], it["file"], name_zh=it.get("name_zh"), name_en=it.get("name_en"),
                tags=it.get("tags") or [], desc=it.get("desc"), canvas=it.get("viewBox"))
    # B：items[]
    m = load_json(ROOT / "子库B/manifest.json")
    for it in m["items"]:
        fname = os.path.basename(it["file"])
        title = it.get("title") or ""
        zh, _, en = title.partition(" / ")
        put("B", it["category"], fname, name_zh=zh, name_en=en or fname,
            tags=it.get("tags") or [], desc=it.get("desc"), canvas=it.get("viewBox"))
    # C：categories[].icons[]（file = slug.svg）
    m = load_json(ROOT / "子库C/manifest.json")
    for c in m["categories"]:
        for it in c["icons"]:
            put("C", c["category"], it["slug"] + ".svg", name_zh=it.get("listName") or it.get("name"),
                name_en=(it.get("en") or "").title(), tags=[], desc=it.get("hint"), canvas="0 0 24 24")
    # D：根 manifest + 每分类 manifest
    m = load_json(ROOT / "子库D/manifest.json")
    for c in m["categories"]:
        for it in c["items"]:
            put("D", c["cat"], it["file"], name_zh=it.get("zh"), name_en=(it.get("en") or "").title(),
                tags=[t for t in (it.get("kw") or "").split(",") if t], desc=it.get("use"),
                canvas=f"0 0 {int(it['w'])} {int(it['h'])}" if it.get("w") else None)
    for d in sorted(os.listdir(ROOT / "子库D/assets")):
        p = ROOT / "子库D/assets" / d / "manifest.json"
        if p.exists():
            m2 = load_json(p)
            for it in m2.get("items", []):
                put("D", d, it["file"], name_zh=it.get("zh"), name_en=(it.get("en") or "").title(),
                    tags=[t for t in (it.get("kw") or "").split(",") if t], desc=it.get("use"))
    # E：assets[]
    m = load_json(ROOT / "子库E/manifest.json")
    for it in m["assets"]:
        put("E", it["cat"], os.path.basename(it["file"]), name_zh=it.get("title_zh"),
            name_en=it.get("title_en"), tags=it.get("tags") or [], desc=it.get("desc"),
            canvas=it.get("canvas"))


SLUG_PREFIX_STRIP = [
    re.compile(r"^\d+[-_]"),                                        # 01-coccus / 02_flagellum
    re.compile(r"^(ns|ar|ge|lb|tb|fl|ch|di|ic|ph|ax|gm)-\d+[-_]"),  # D 前缀+序号
    re.compile(r"^(ns|ar|ge|lb|tb|fl|ch|di|ic|ph|ax|gm)-"),         # D 前缀（无序号）
    re.compile(r"^[a-z]{2}-"),                                      # E 双字母前缀
]


def make_slug(fname):
    stem = fname[:-4].replace("_", "-")
    for pat in SLUG_PREFIX_STRIP:
        new = pat.sub("", stem, count=1)
        if new != stem:
            stem = new
            break
    stem = re.sub(r"-+", "-", stem).strip("-").lower()
    return stem


def main():
    load_meta()
    rows = []
    for sub in ["A", "B", "C", "D", "E"]:
        adir = ROOT / SUBS[sub] / "assets"
        for cat in sorted(os.listdir(adir)):
            cdir = adir / cat
            if not cdir.is_dir() or cat == "license":
                continue
            split = SPLIT_RULES.get((sub, cat))
            whole = WHOLE_MAP.get((sub, cat))
            files = sorted(f for f in os.listdir(cdir) if f.endswith(".svg"))
            for f in files:
                if split:
                    subdir, fmt = split(f)
                elif whole:
                    subdir, fmt = whole
                else:
                    raise SystemExit(f"未映射源分类: {sub}/{cat}")
                meta = META.get((sub, cat, f), {})
                rows.append({
                    "src": f"{SUBS[sub]}/assets/{cat}/{f}",
                    "sub": sub, "src_cat": cat,
                    "subdir": subdir, "format": fmt,
                    "name_zh": meta.get("name_zh") or "",
                    "name_en": meta.get("name_en") or "",
                    "tags": meta.get("tags") or [],
                    "desc": meta.get("desc") or "",
                    "canvas": meta.get("canvas") or "",
                })
                rows[-1]["slug0"] = make_slug(f)

    assert len(rows) == 2830, f"源文件数 {len(rows)} != 2830"
    src_cats = {(r["sub"], r["src_cat"]) for r in rows}
    print(f"源分类数: {len(src_cats)}（预期 65）")

    # 全局 slug 唯一化
    used = {}
    for r in rows:
        s = r["slug0"]
        if s in used:
            used[s] += 1
            r["slug"] = f"{s}-{used[s]}"
        else:
            used[s] = 1
            r["slug"] = s
    slugs = [r["slug"] for r in rows]
    assert len(set(slugs)) == len(slugs), "slug 全局冲突"

    # 二级目录内 NNN 编号
    order = {k: i for i, k in enumerate(SUBDIRS)}
    srcc = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    rows.sort(key=lambda r: (order[r["subdir"]], srcc[r["sub"]], r["src_cat"], r["src"]))
    counters = {}
    cat_dirname = {c[0]: c[1] for c in CATEGORIES}
    for r in rows:
        counters[r["subdir"]] = counters.get(r["subdir"], 0) + 1
        r["nnn"] = f"{counters[r['subdir']]:03d}"
        catno = SUBDIRS[r["subdir"]][0]
        r["cat_no"] = catno
        r["cat_dir"] = f"{catno}-{cat_dirname[catno]}"
        r["dst"] = f"assets/{r['cat_dir']}/{r['subdir']}/{r['nnn']}-{r['slug']}.svg"
        r["series"] = SERIES[r["sub"]]

    names = [os.path.basename(r["dst"]) for r in rows]
    assert len(set(names)) == len(names), "文件名字符串存在重复"

    (ROOT / "tools/reorg/move-map.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    # 台账
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    ledger = []
    for r in rows:
        ledger.append({
            "file": r["dst"],
            "series": r["series"],
            "format": r["format"],
            "category": r["cat_dir"],
            "science": {"verdict": "pending", "issues": [], "fixes": []},
            "art": {"verdict": "pending", "issues": [], "fixes": []},
            "conflict": {"verdict": "pending", "decision": ""},
            "text_zh_en": {"status": "pending"},
            "reviewed_at": "",
        })
    assert len(ledger) == 2830
    (ROOT / "qa/review-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")

    # REORG-PLAN.md
    catname = {c[0]: c[2] for c in CATEGORIES}
    lines = []
    lines.append("# REORG-PLAN（过程文件，发布前删除）\n")
    lines.append(f"生成时间：{now} · 源文件 2830 · 目标 12 大类 / 44 二级目录\n")
    lines.append("## 一、65 个源分类 → 目标路径映射总表\n")
    lines.append("| 源 | 数量 | 目标大类/二级目录 | format |")
    lines.append("|---|---|---|---|")
    from collections import Counter
    cnt = Counter((r["sub"], r["src_cat"], r["cat_dir"], r["subdir"], r["format"]) for r in rows)
    for (sub, scat, catdir, subdir, fmt), n in sorted(cnt.items()):
        zh = catname[catdir.split("-")[0]]
        lines.append(f"| 子库{sub} {scat} | {n} | {catdir}（{zh}）/{subdir} | {fmt} |")
    lines.append(f"\n源分类合计：{len(src_cats)} 个，全部落位。\n")
    lines.append("## 二、5 个“逐张判”源类的逐文件归属清单\n")
    for sub, scat in [("A", "05-eco-seq"), ("B", "microscopy-scale"), ("C", "signage-flow"),
                      ("D", "natural-sciences"), ("D", "lab-equipment")]:
        sel = [r for r in rows if r["sub"] == sub and r["src_cat"] == scat]
        lines.append(f"\n### 子库{sub} {scat}（{len(sel)} 个）\n")
        lines.append("| 源文件 | 目标 |")
        lines.append("|---|---|")
        for r in sorted(sel, key=lambda x: x["src"]):
            lines.append(f"| `{r['src']}` | `{r['dst']}` |")
    lines.append("\n## 三、逐张判裁决说明\n")
    lines.append("- **A 05-eco-seq**：01–16 生境→05/habitats；17–26 组学工作流→06/omics-workflow；27–30 组学数据图→02/omics-charts；31–38 生物技术应用→05/biotech-applications（与任务书映射一致）。")
    lines.append("- **B microscopy-scale**：21–33 号（size_*）为纳米—微米尺度对比/比例尺→10/scale-reference（13 个）；其余 36 个镜检/染色/检测技术→06/microscopy-detection。")
    lines.append("- **C signage-flow**：sign-* 13 个安全标志→09/signage；arrow/badge/bracket/connector/flow/legend 19 个→10/connectors。")
    lines.append("- **D natural-sciences**：分子结构（核酸 01–08、膜 20–25、生化分子 26–38，共 27）→02/mol-structures；细菌形态 39–41→01/morphology-arrangement；病毒 42–44 与朊粒 49→01/viruses-phages；真核细胞/细胞器/组织 09–19、45–48、50–59、70→01/eukaryotic-cells-organelles；食物链/物质循环/地质过程 60–69→05/interactions；蒸腾/光合 71–72→03/metabolism。逐张判结果 01:33 / 02:27 / 03:2 / 05:10，总数 72 不变。")
    lines.append("- **D lab-equipment**：器皿/耗材/手持支架工具 47 个→07/general-labware；带动力/电子/柜式装置 17 个→08/general-apparatus。\n")
    lines.append("## 四、命名与编号\n")
    lines.append("- 目标文件名 `NNN-slug-en.svg`：NNN 为二级目录内三位序号；slug 由源文件名派生（剥离数字/子库前缀、下划线转连字符、小写）。")
    lines.append("- 全局唯一：slug 全库去重（冲突自动加 `-2/-3` 后缀），文件名字符串全库唯一（脚本断言）。")
    lines.append("- 英文版 `NNN-slug-en.en.svg`（P4 生成）。\n")
    lines.append("## 五、P3 审查协议（摘要）\n")
    lines.append("逐文件：渲染出图 + 程序化检查（零脚本/外链/位图、字面 hex、CJK 字体链、字号下限、标签重叠、安全标志对称、许可元数据）+ 视觉审查（科学性/艺术性双清单）；同二级目录跨 series 同主题逐对裁决写入 conflict 字段。台账随批次更新。\n")

    (ROOT / "REORG-PLAN.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"rows={len(rows)}")
    tc = Counter(r["cat_dir"] for r in rows)
    for c in CATEGORIES:
        key = f"{c[0]}-{c[1]}"
        print(f"  {key}: {tc[key]}")
    print("ledger rows:", len(ledger))


if __name__ == "__main__":
    main()
