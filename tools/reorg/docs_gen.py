# -*- coding: utf-8 -*-
"""P4 文档双语生成器：README / README-SERIES / 12×SPEC / CONTRIBUTING / NOTICE。

中英两版由同一数据渲染，保证内容与结构对等。
用法：python3 tools/reorg/docs_gen.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

CATS = [
    ("01", "cells-microbes", "细胞与微生物形态结构", "Cells & Microbes: Morphology and Structure"),
    ("02", "genetics-omics", "遗传信息与组学", "Genetics & Omics"),
    ("03", "metabolism-phenotype", "代谢与生理表型", "Metabolism & Physiological Phenotype"),
    ("04", "phylogeny-evolution", "系统发育与进化", "Phylogeny & Evolution"),
    ("05", "ecology-biotech", "生态·生境与应用", "Ecology, Habitats & Applications"),
    ("06", "lab-methods", "实验方法与流程", "Lab Methods & Workflows"),
    ("07", "glassware-consumables", "器皿·耗材与通用器材", "Glassware, Consumables & General Labware"),
    ("08", "instruments-apparatus", "仪器与装置", "Instruments & Apparatus"),
    ("09", "safety-signage", "安全·防护与标识", "Safety & Signage"),
    ("10", "figure-elements", "图版构件", "Figure Elements"),
    ("11", "diagrams-charts", "图示语法·流程与图表", "Diagrams, Flows & Charts"),
    ("12", "icons-ui", "通用图标与 UI", "Icons & UI"),
]

SERIES = [
    ("classic", "经典科研插画", "简洁线稿+低饱和平涂，面向教材与综述正文。",
     "Classic scientific illustration", "Clean line work with flat low-saturation fills, for textbooks and review figures."),
    ("atlas", "微生物图谱", "图谱级细节：标注引线、比例尺、色盲安全语义色。",
     "Microbe atlas", "Atlas-level detail: leader-line labels, scale bars, color-blind-safe semantic colors."),
    ("icon24", "24×24 线性图标", "统一网格与线宽，适合界面与图例小尺寸复用。",
     "24×24 line icons", "Uniform grid and stroke, ideal for UI and small in-figure use."),
    ("primitives", "科研通用图元", "跨学科通用构件：箭头、图表骨架、电路与流程符号。",
     "General scientific primitives", "Cross-discipline building blocks: arrows, chart skeletons, circuit and flow symbols."),
    ("labflow", "实验室流程与设备", "设备框图、流程节点与安全标识，强调流程走向可读性。",
     "Lab workflow & equipment", "Equipment block diagrams, workflow nodes and safety signage with readable flow direction."),
]

FORMATS = [
    ("illustration", "插画", "Illustration"),
    ("diagram", "示意图表", "Diagram / chart"),
    ("icon", "图标（currentColor 可换肤）", "Icon (currentColor, re-tintable)"),
]


def load_manifest():
    return json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))


def cat_stats():
    top = load_manifest()
    rows = []
    total = 0
    for c in top["categories"]:
        n = len([p for p in (ASSETS / c["id"]).rglob("*.svg") if not p.name.endswith(".en.svg")])
        total += n
        rows.append((c["id"], n, c["name_zh"], c["name_en"]))
    assert total == 2830, total
    return rows, total


def subdirs_of(cat_id):
    cm = json.loads((ASSETS / cat_id / "manifest.json").read_text(encoding="utf-8"))
    return [(s["id"], s["name_zh"], s["name_en"], s["count"]) for s in cm["subdirs"]]


def format_counts():
    c = Counter()
    for p in ASSETS.rglob("*.svg"):
        if p.name.endswith(".en.svg"):
            continue
    top = load_manifest()
    for cat in top["categories"]:
        cm = json.loads((ASSETS / cat["id"] / "manifest.json").read_text(encoding="utf-8"))
        for s in cm["subdirs"]:
            sm = json.loads((ASSETS / cat["id"] / s["id"] / "manifest.json").read_text(encoding="utf-8"))
            for it in sm["items"]:
                c[it["format"]] += 1
    return c


def write(readme_zh, readme_en, series_zh, series_en, specs, contrib_zh, contrib_en,
          notice_zh, notice_en):
    (ROOT / "README.md").write_text(readme_zh, encoding="utf-8")
    (ROOT / "README.en.md").write_text(readme_en, encoding="utf-8")
    (ROOT / "README-SERIES.md").write_text(series_zh, encoding="utf-8")
    (ROOT / "README-SERIES.en.md").write_text(series_en, encoding="utf-8")
    for cat_id, fn_zh, fn_en in specs:
        (ASSETS / cat_id / "SPEC.md").write_text(fn_zh, encoding="utf-8")
        (ASSETS / cat_id / "SPEC.en.md").write_text(fn_en, encoding="utf-8")
    (ROOT / "CONTRIBUTING.md").write_text(contrib_zh, encoding="utf-8")
    (ROOT / "CONTRIBUTING.en.md").write_text(contrib_en, encoding="utf-8")
    (ROOT / "NOTICE").write_text(notice_zh, encoding="utf-8")
    (ROOT / "NOTICE.en.md").write_text(notice_en, encoding="utf-8")


def main():
    rows, total = cat_stats()
    fc = format_counts()

    # ---- README ----
    zh = []
    zh.append("# SciGlyph · 绘图素材库（科研绘图 SVG 素材，v1.0.0）\n")
    zh.append(f"**SciGlyph** —— 面向科研绘图的开源 SVG 素材库：**{total} 个主素材**（另有 260 个 `.en.svg` 英文文本变体），"
              "按 12 个学科大类组织，含五个画风系列与三种形态（插画/示意图/图标）。\n")
    zh.append("> ⚠️ **AI 生成声明**：本库全部素材由 AI（大模型）辅助生成，并经人工审查与程序化质检；"
              "虽经逐文件校核，仍可能存在科学性或事实性误差。**正式使用（尤其是论文发表）前，"
              "请对照权威文献与官方标准自行核实图中信息的准确性。**\n")
    zh.append("## 预览\n")
    zh.append("![全库总览](preview/sciglyph-overview.png)\n")
    zh.append("![五个画风系列](preview/sciglyph-series.png)\n")
    zh.append("![器皿·仪器·安全](preview/sciglyph-lab.png)\n")
    zh.append("![图版构件·图表·图标](preview/sciglyph-figures.png)\n")
    zh.append("- 许可：素材 **CC BY 4.0**（权利人 ZengZichao）；工具与页面代码 **MIT**。")
    zh.append("- 英文文档：[README.en.md](README.en.md)；画风系列说明：[README-SERIES.md](README-SERIES.md) / [README-SERIES.en.md](README-SERIES.en.md)。")
    zh.append("- 浏览：直接双击打开根目录 `index.html`（离线可用，支持中英切换与亮暗主题）。")
    zh.append("- 在线画廊：推送到 GitHub 后由 Pages 自动发布（见 [DEPLOY.md](DEPLOY.md)）。")
    zh.append("- 引用：见 [CITATION.cff](CITATION.cff) 与 [NOTICE](NOTICE)。\n")
    zh.append("## 12 个学科大类\n")
    zh.append("| 编号 | 大类 | 素材数 |")
    zh.append("|---|---|---|")
    for cid, n, zhen, en in rows:
        zh.append(f"| {cid} | {zhen}（{en}） | {n} |")
    zh.append(f"| | **合计** | **{total}** |\n")
    zh.append(f"形态分布：插画 {fc['illustration']} · 示意图表 {fc['diagram']} · 图标 {fc['icon']}。\n")
    zh.append("## 使用约定\n")
    zh.append("- 文件名 `NNN-slug-en.svg`（三位序号 + 全局唯一 kebab 英文 slug）；含中文渲染文本的素材配有同名 `.en.svg` 英文版。")
    zh.append("- 全部素材：零脚本、零外链、零内嵌位图；颜色为字面 hex；中文版字体链含 CJK 回退族。")
    zh.append("- 每个素材携带 `data-license=\"CC-BY-4.0\" data-copyright=\"ZengZichao\"`；manifest 每条含 license/license_uri/attribution。")
    zh.append("- 质检总闸门：`python3 tools/check_repo.py`（结构/命名/manifest/SVG 安全/许可/字体链/字号下限/标签零重叠/文字出画/可渲染性/安全标志对称/zh-en 配对）；画廊与素材的一致性由 `python3 tools/check_site.py` 校验。\n")
    zh.append("## 目录结构\n")
    zh.append("```")
    zh.append("绘图素材库/")
    zh.append("├── README.md / README.en.md / README-SERIES.md / README-SERIES.en.md")
    zh.append("├── LICENSE (MIT) / LICENSE-ASSETS (CC BY 4.0) / NOTICE / CITATION.cff")
    zh.append("├── index.html            # 唯一画廊（搜索/过滤/中英切换/亮暗主题）")
    zh.append("├── preview/              # 整合预览图（sciglyph-*.png）")
    zh.append("├── assets/01..12-*/      # 12 大类，每类含子目录与 SPEC")
    zh.append("└── tools/                # 质检与构建工具")
    zh.append("```")
    readme_zh = "\n".join(zh)

    en = []
    en.append("# SciGlyph — Scientific Illustration Asset Library (SVG, v1.0.0)\n")
    en.append(f"**SciGlyph** is an open SVG library for scientific figure-making: **{total} assets** "
              "(plus 260 `.en.svg` English-text variants), organized into 12 discipline categories, "
              "five visual series and three formats (illustration / diagram / icon).\n")
    en.append("> ⚠️ **AI-generated notice**: every asset in this library was generated with the assistance of AI models, "
              "followed by human review and automated QA checks. Errors may still remain — **before formal use "
              "(especially publication), verify the scientific accuracy of each figure against authoritative sources.**\n")
    en.append("## Preview\n")
    en.append("![Overview](preview/sciglyph-overview.png)\n")
    en.append("![Five visual series](preview/sciglyph-series.png)\n")
    en.append("![Glassware, instruments and safety](preview/sciglyph-lab.png)\n")
    en.append("![Figure elements, charts and icons](preview/sciglyph-figures.png)\n")
    en.append("- License: assets **CC BY 4.0** (© ZengZichao); tooling and pages **MIT**.")
    en.append("- Chinese documentation: [README.md](README.md); series guide: [README-SERIES.en.md](README-SERIES.en.md) / [README-SERIES.md](README-SERIES.md).")
    en.append("- Browse: open `index.html` from the repo root (works offline, with zh/en toggle and light/dark themes).")
    en.append("- Online gallery: pushed to GitHub and published automatically via Pages (see [DEPLOY.en.md](DEPLOY.en.md)).")
    en.append("- Citation: see [CITATION.cff](CITATION.cff) and [NOTICE](NOTICE).\n")
    en.append("## 12 categories\n")
    en.append("| ID | Category | Assets |")
    en.append("|---|---|---|")
    for cid, n, zhen, en_name in rows:
        en.append(f"| {cid} | {en_name} | {n} |")
    en.append(f"| | **Total** | **{total}** |\n")
    en.append(f"Format mix: illustration {fc['illustration']} · diagram {fc['diagram']} · icon {fc['icon']}.\n")
    en.append("## Conventions\n")
    en.append("- File names follow `NNN-slug-en.svg` (3-digit number + globally unique kebab-case English slug); assets with rendered Chinese text ship with a matching `.en.svg` English variant.")
    en.append("- Every asset: no scripts, no external references, no embedded bitmaps; literal hex colors; Chinese text uses a CJK-fallback font stack.")
    en.append('- Each file carries `data-license="CC-BY-4.0" data-copyright="ZengZichao"`; every manifest entry includes license/license_uri/attribution.')
    en.append("- Quality gate: `python3 tools/check_repo.py` (structure, naming, manifest, SVG safety, licensing, font stacks, minimum type size, zero label overlap, no text overflow, renderability, safety-symbol symmetry, zh/en pairing); `python3 tools/check_site.py` keeps the gallery and the assets in sync.\n")
    en.append("## Layout\n")
    en.append("```")
    en.append("绘图素材库/")
    en.append("├── README.md / README.en.md / README-SERIES.md / README-SERIES.en.md")
    en.append("├── LICENSE (MIT) / LICENSE-ASSETS (CC BY 4.0) / NOTICE / CITATION.cff")
    en.append("├── index.html            # single gallery (search/filter/zh-en/light-dark)")
    en.append("├── preview/              # consolidated preview images (sciglyph-*.png)")
    en.append("├── assets/01..12-*/      # 12 categories, each with subfolders and a SPEC")
    en.append("└── tools/                # QA and build tooling")
    en.append("```")
    readme_en = "\n".join(en)

    # ---- README-SERIES ----
    sz = ["# 五个画风系列\n"]
    sz.append("全库素材分属五个画风系列（`series` 字段，manifest 与画廊可过滤）：\n")
    sz.append("| series | 说明 | 定位 |")
    sz.append("|---|---|---|")
    for k, zn, zd, _en, _ed in SERIES:
        sz.append(f"| `{k}` | {zn} | {zd} |")
    sz.append("\n三种形态（`format` 字段）：\n")
    sz.append("| format | 含义 |")
    sz.append("|---|---|")
    for k, zn, _en in FORMATS:
        sz.append(f"| `{k}` | {zn} |")
    sz.append("")
    series_zh = "\n".join(sz)

    se = ["# Five visual series\n"]
    se.append("The library is organized into five visual series (the `series` field; filterable in manifests and the gallery):\n")
    se.append("| series | Description | Positioning |")
    se.append("|---|---|---|")
    for k, _zn, _zd, en_, ed in SERIES:
        se.append(f"| `{k}` | {en_} | {ed} |")
    se.append("\nThree formats (the `format` field):\n")
    se.append("| format | Meaning |")
    se.append("|---|---|")
    for k, _zn, en_ in FORMATS:
        se.append(f"| `{k}` | {en_} |")
    se.append("")
    series_en = "\n".join(se)

    # ---- per-category SPEC ----
    specs = []
    spec_zh = {
        "01": ("本类覆盖原核/真核细胞与病毒的形态、结构与排列。子目录按“研究对象”划分：形态与排列、细胞结构、细胞包膜、附属结构与运动、古菌、病毒与噬菌体、真核细胞与细胞器。"
               "科学口径：细菌形态与排列沿用通行教材；古菌门级命名遵循 GTDB；病毒形态为示意级（非电镜比例复刻）。"),
        "02": ("本类覆盖遗传信息及其分析呈现：基因与移动遗传元件、序列图形、群体基因组、比较基因组与泛基因组、分子生态、分子结构、组学数据图。"
               "科学口径：遗传学示意图遵循中心法则与通行机制命名；群体遗传学术语与公式（θ=4Neμ 等）按经典口径。"),
        "03": ("本类覆盖微生物代谢途径与生理表型：代谢（能量代谢、物质循环、耐受机制）与表型（革兰反应、抗酸、溶血、菌落形态、耐药表型等）。"
               "科学口径：途径图按教科书通用画法，电子受体/供体与末端产物标注正确。"),
        "04": ("本类覆盖系统发育与进化：树骨架、树注释、演化过程、命名法规。"
               "科学口径：树形为示意级；节点支持/后验/尺度条等注释件语义明确；命名法规缩写（sp. nov.、comb. nov. 等）符合 ICNP 惯例。"),
        "05": ("本类覆盖微生物生态与生物技术应用：生境（自然环境、人体部位、极端环境）、互作与物质流、生物技术应用。"
               "科学口径：生境图与互作图为概念示意；地质/圈层过程图为教材通用画法。"),
        "06": ("本类覆盖实验方法与流程：培养与生化鉴定、分析流程、组学工作流、镜检与检测技术。"
               "科学口径：操作步骤次序正确，参数标注（温度/时间/离心力）为常见参考值。"),
        "07": ("本类覆盖器皿、耗材与通用器材：玻璃器皿、储存与耗材、支架与工具、通用器材。"
               "科学口径：器皿比例与结构（嘴、刻度、磨口、容积线）符合实验室实物。"),
        "08": ("本类覆盖仪器与装置：分析仪器、生命科学仪器、热学与机械、分离与流控、移液与液体处理、电气器材、监测与传感、通用装置。"
               "科学口径：模块框图的光路/气路/流程走向自洽；仪器外形为示意级。"),
        "09": ("本类覆盖安全、防护与标识：危害警示标志、防护与应急、人员行为、安全标识。"
               "合规口径：GHS 象形图与 ISO 7010 安全标志遵循公开几何定义（生物危害/电离辐射三叶已做旋转对称校验）；禁止类标志红环+斜杠、指令类蓝圆为标准形态。"),
        "10": ("本类覆盖图版构件：比例与尺度参照、图版布局、箭头与连接件、几何与数学、表格与框线、标签与标牌、流程连接符。"
               "用途：论文图版的通用件——比例尺、图例、面板骨架、误差线等。"),
        "11": ("本类覆盖图示语法、流程与图表：流程图语法、软件图与 UML、图表与绘图、工艺流程与单元操作（P&ID）、物理光路与电路。"
               "合规口径：流程图形状遵循 ANSI/ISO 5807；P&ID 参照 ISA-5.1 公开符号；电路符号为 IEC/ANSI 常用画法。"),
        "12": ("本类覆盖通用图标与 UI：线性图标与彩色点缀图标两套。全部为 24×24 或 48×48 网格，适合界面与图内小尺寸使用。"),
    }
    spec_en = {
        "01": ("Covers morphology, structure and arrangement of prokaryotic/eukaryotic cells and viruses. Subfolders follow the object of study: morphology & arrangement, cell structures, cell envelope, appendages & motility, archaea, viruses & phages, eukaryotic cells & organelles. "
               "Scientific conventions: bacterial morphology/arrangement follows standard textbooks; archaeal phylum names follow GTDB; virus shapes are schematic rather than EM-faithful."),
        "02": ("Covers genetic information and its analysis: genes & MGE, sequence graphics, population genomics, comparative & pan-genomics, molecular ecology, molecular structures, omics charts. "
               "Scientific conventions: mechanisms follow the central dogma and standard genetics nomenclature; population-genetics terms and formulas (θ = 4Neμ) follow classic usage."),
        "03": ("Covers microbial metabolism and physiological phenotype: metabolism (energy, element cycling, stress tolerance) and phenotype (Gram reaction, acid-fastness, hemolysis, colony morphology, resistance). "
               "Scientific conventions: pathways follow textbook conventions; electron donors/acceptors and end products are labeled correctly."),
        "04": ("Covers phylogeny and evolution: tree skeletons, tree annotation, evolutionary process, nomenclature. "
               "Scientific conventions: trees are schematic; support/posterior/scale-bar annotations carry explicit semantics; nomenclature abbreviations (sp. nov., comb. nov., …) follow ICNP usage."),
        "05": ("Covers microbial ecology and biotech applications: habitats (natural environments, body sites, extreme environments), interactions & matter flow, biotech applications. "
               "Scientific conventions: habitat and interaction art is conceptual; geosphere/cycle diagrams follow textbook depictions."),
        "06": ("Covers lab methods and workflows: culture & biochemical tests, analysis pipelines, omics workflows, microscopy & detection. "
               "Scientific conventions: step order is correct; parameter labels (temperature/time/g-force) are common reference values."),
        "07": ("Covers glassware, consumables and general labware: glassware, storage & consumables, hardware & tools, general labware. "
               "Scientific conventions: proportions and details (spouts, graduations, stoppers, graduation marks) match real labware."),
        "08": ("Covers instruments and apparatus: analytical, life-science, thermal & mechanical, separation & fluidics, liquid handling, electrical equipment, monitoring & sensors, general apparatus. "
               "Scientific conventions: block-diagram optical/gas/flow paths are self-consistent; exteriors are schematic."),
        "09": ("Covers safety and signage: hazard signs, PPE & emergency, personnel behavior, safety signage. "
               "Compliance: GHS pictograms and ISO 7010 signs follow the published geometry (biohazard and ionizing-radiation trefoils are rotation-symmetry verified); prohibition (red ring + slash) and mandatory (blue disc) forms are standard."),
        "10": ("Covers figure elements: scale reference, figure layout, arrows & connectors, geometry & math, tables & frames, labels & tags, flow connectors. "
               "Use: generic building blocks for publication figures — scale bars, legends, panel skeletons, error bars."),
        "11": ("Covers diagram syntax, flows and charts: flowchart syntax, software diagrams & UML, charts & plots, P&ID & unit operations, physics optics & circuits. "
               "Compliance: flowchart shapes follow ANSI/ISO 5807; P&ID symbols follow published ISA-5.1 symbology; circuit symbols follow common IEC/ANSI practice."),
        "12": ("Covers general icons and UI: two icon sets (line icons and color-accent icons). All sit on a 24×24 or 48×48 grid for UI and small in-figure use."),
    }
    for cid, _dir, zhen, en_name in CATS:
        subs = subdirs_of(f"{cid}-{_dir}")
        z = [f"## {cid} {zhen}（{en_name}）\n"]
        z.append(spec_zh[cid] + "\n")
        z.append("| 子目录 | 数量 |")
        z.append("|---|---|")
        for sid, szh, _se, n in subs:
            z.append(f"| `{sid}` | {n} |")
        n_total = sum(n for *_x, n in subs)
        z.append(f"\n共 {n_total} 个素材 · 规格：命名 `NNN-slug-en.svg`、许可 CC BY 4.0（元数据内嵌）、"
                 "含中文渲染文本的素材配 `.en.svg`。\n")
        e = [f"## {cid} {en_name}\n"]
        e.append(spec_en[cid] + "\n")
        e.append("| Subfolder | Count |")
        e.append("|---|---|")
        for sid, _szh, sen, n in subs:
            e.append(f"| `{sid}` | {n} |")
        e.append(f"\n{n_total} assets · conventions: names `NNN-slug-en.svg`, CC BY 4.0 (metadata embedded), "
                 "assets with rendered Chinese text ship with `.en.svg`.\n")
        specs.append((f"{cid}-{_dir}", "\n".join(z), "\n".join(e)))

    # ---- CONTRIBUTING ----
    cz = """# 贡献指南\n
## 环境依赖\n
- python3（标准库即可跑全部闸门；渲染预览另需 cairosvg/Pillow）
- node（jsdom，仅画廊交互测试需要）\n
## 新增/修改素材\n
1. 放入对应的 `assets/<大类>/<子目录>/`，命名 `NNN-slug-en.svg`（序号接续，slug 全库唯一、纯 ASCII 小写 kebab）。
2. SVG 硬性要求：零脚本/零外链/零内嵌位图；颜色一律字面 hex；中文渲染文本字体链用
   `'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif`（英文版 Inter,Helvetica,Arial）；
   字号 ≥ 下限（大画布 7、微型图标 4）；标签零重叠、文字不出画。
3. 带中文渲染文本的素材必须同时提交 `.en.svg`（可用 `tools/derive_en_variants.py` 派生后人工润色）。
4. 更新所在子目录 `manifest.json`（name_zh/name_en/tags≥3/series/format/canvas），顶层与类别 manifest 同步计数。
5. 跑 `python3 tools/check_repo.py` 必须全绿。
6. 提交信息一行说明改动范围。\n
## 闸门明细\n
`tools/check_repo.py` 校验：目录结构与二级目录数、文件名与全库唯一性、序号连续、manifest 严格字段（含 en 配对）、
SVG 安全（脚本/外链/位图/非字面颜色）、许可元数据、CJK 字体链、字号下限、标签零重叠、文字出画、安全标志旋转对称、zh-en 配对完整。
`tools/legibility.py`、`tools/fix_label_overlap.py --check`、`tools/fix_text_overflow.py`、`tools/check_symbol_symmetry.py`
可单独调用定位问题；`tools/derive_en_variants.py --strict` 校验双语覆盖。
"""
    ce = """# Contributing\n
## Prerequisites\n
- python3 (the standard library runs every gate; cairosvg/Pillow only for preview rendering)
- node (jsdom, only for gallery interaction tests)\n
## Adding or editing assets\n
1. Place files in `assets/<category>/<subfolder>/` named `NNN-slug-en.svg` (continuing numbers; slug globally unique, lowercase ASCII kebab-case).
2. Hard SVG requirements: no scripts, no external references, no embedded bitmaps; literal hex colors only; rendered Chinese text uses
   `'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif` (English variants use Inter,Helvetica,Arial);
   font size at or above the floor (7 for large canvases, 4 for micro icons); zero label overlap; no text outside the viewBox.
3. Assets with rendered Chinese text must ship an `.en.svg` variant (derive with `tools/derive_en_variants.py`, then polish).
4. Update the subfolder `manifest.json` (name_zh/name_en/tags>=3/series/format/canvas); keep category and root manifests in sync.
5. `python3 tools/check_repo.py` must pass fully.
6. One-line commit messages describing the scope.\n
## Gate details\n
`tools/check_repo.py` validates: directory structure and subfolder counts, file names and global uniqueness, sequential numbering,
strict manifest fields (including en pairing), SVG safety (scripts/external refs/bitmaps/non-literal colors), license metadata,
CJK font stacks, minimum type size, zero label overlap, text overflow, safety-symbol rotational symmetry, zh/en pairing.
`tools/legibility.py`, `tools/fix_label_overlap.py --check`, `tools/fix_text_overflow.py` and `tools/check_symbol_symmetry.py`
can be run individually to locate issues; `tools/derive_en_variants.py --strict` verifies bilingual coverage.
"""
    # ---- NOTICE ----
    nz = """SciGlyph · 绘图素材库 NOTICE\n
版权所有 (c) 2026 ZengZichao (https://github.com/ZengZichao)\n
1. assets/ 下的全部 SVG 素材以 CC BY 4.0 授权：
   https://creativecommons.org/licenses/by/4.0/
   每个素材文件内嵌 data-license="CC-BY-4.0" 与 data-copyright="ZengZichao"。
   使用时请署名：ZengZichao · CC BY 4.0（附链接即可）。\n
2. tools/ 与 index.html 等代码以 MIT 授权（见 LICENSE）。\n
3. AI 生成声明：本库素材由 AI（大模型）辅助生成，经人工审查与程序化质检后发布；
   仍可能存在科学性或事实性误差。使用者应自行核实图中信息（形态、数值、术语、
   安全标志语义等）的准确性，正式发表前请对照权威文献与官方标准。\n
4. 安全标志（09-safety-signage）依据 ISO 361 / ISO 7010 / GHS 的公开几何定义绘制，
   仅为教学与研究示意用途；正式合规标识请以各国标准发布物为准。
"""
    ne = """SciGlyph · Library NOTICE\n
Copyright (c) 2026 ZengZichao (https://github.com/ZengZichao)\n
1. All SVG assets under assets/ are licensed CC BY 4.0:
   https://creativecommons.org/licenses/by/4.0/
   Every file embeds data-license="CC-BY-4.0" and data-copyright="ZengZichao".
   Attribution: ZengZichao · CC BY 4.0 (a link suffices).\n
2. Code in tools/ and index.html is MIT-licensed (see LICENSE).\n
3. AI-generated notice: the assets were produced with the assistance of AI models,
   then human-reviewed and checked by automated QA. Errors may still remain — users
   are responsible for verifying the accuracy of any figure (morphology, values,
   terminology, safety-sign semantics) against authoritative sources before formal use.\n
4. Safety signs (09-safety-signage) are drawn after the published geometry of
   ISO 361 / ISO 7010 / GHS, for teaching and research illustration only; use
   officially issued artwork for regulatory signage.
"""
    write(readme_zh, readme_en, series_zh, series_en, specs, cz, ce, nz, ne)
    print("文档生成：README×2 / README-SERIES×2 / SPEC×24 / CONTRIBUTING×2 / NOTICE×2")


if __name__ == "__main__":
    main()
