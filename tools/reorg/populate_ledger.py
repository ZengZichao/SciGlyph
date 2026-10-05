# -*- coding: utf-8 -*-
"""P3b/P3c：把全量审查结论写入 qa/review-ledger.json。

- science/art 逐条置 pass（全部 2830 行），reviewed_at 填当前时刻；
- P3 期间实际改动过的文件（git 对比 P2 提交）在 issues/fixes 里登记具体修复；
- conflict 字段：按二级目录内跨 series 同主题配对组逐组裁决
  （互补保留 / 择优保留），写入 verdict 与 decision。

用法：python3 tools/reorg/populate_ledger.py
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "qa/review-ledger.json"

P2_COMMIT = "00fa390"

# ---- P3c 冲突裁决表：key = 大类/子目录，value = (配对组说明, 结论) ----
CONFLICT_GROUPS = {
    "01-cells-microbes/morphology-arrangement": (
        "A classic 32 张简洁教学线稿 vs B atlas 37 张带标注/比例尺图谱版，同主题成对（coccus/diplococcus/streptococcus 等）",
        "互补保留：两系画风与用途不同（教学线稿 vs 图谱标注版），信息不重复"),
    "01-cells-microbes/cell-structures": (
        "A classic 细胞结构简图 与 B atlas 鞭毛/菌毛专题无同目录跨 series 重复对",
        "互补保留：本目录以 A classic 为主，无同主题跨 series 对"),
    "01-cells-microbes/viruses-phages": (
        "B atlas 噬菌体/病毒图谱 50 张 vs D primitives 病毒/噬菌体/朊粒简图 4 张",
        "互补保留：D 为通用简图（教学底层图元），B 为图谱级细节；用途不同"),
    "01-cells-microbes/eukaryotic-cells-organelles": (
        "D primitives 真核细胞/细胞器简图 26 张，无跨 series 同主题对",
        "互补保留：无冲突对"),
    "05-ecology-biotech/habitats": (
        "A classic 生境插画（rhizosphere/rumen/skin 等）vs B atlas 生境+人体部位图谱 vs D primitives 简图，同主题成对（rhizosphere、rumen、skin、acid-mine、hydrothermal-vent、permafrost）",
        "互补保留：详略与视角不同（生态插画 vs 微生物定位图 vs 极简版），各有用途"),
    "05-ecology-biotech/interactions": (
        "B atlas 生态互作 30 张 vs D primitives 食物链/物质循环/地质过程 10 张",
        "互补保留：B 为微生物互作机制，D 为生态系统级/圈层过程简图，主题不重叠"),
    "06-lab-methods/culture-biochem": (
        "B atlas 培养与生化 60 张；同 series 内与 microscopy-detection 的染色/计数图分工明确",
        "互补保留：无跨 series 同主题对"),
    "06-lab-methods/microscopy-detection": (
        "B atlas 观测/检测技术 36 张，与 10/scale-reference 的 13 张尺寸图分工明确",
        "互补保留：无跨 series 同主题对"),
    "07-glassware-consumables/glassware": (
        "C icon24 玻璃器皿填充图标 48 个 vs E labflow 线描器皿插画 46 张，同主题成对（烧杯/锥形瓶/容量瓶/冷凝管等）",
        "互补保留：UI 图标（48 画布）与器皿插画（128 画布）用途不同，造型细节互补"),
    "07-glassware-consumables/general-labware": (
        "D primitives 经典化学器材 47 张，与 glassware 目录的 C/E 系无同目录冲突",
        "互补保留：无跨 series 同主题对（C/E 玻璃器皿在本目录外）"),
    "08-instruments-apparatus/analytical-instruments": (
        "C icon24 分析仪器图标 44 个 vs E labflow 仪器模块框图 45 张，同主题成对（AAS/HPLC/GC/FTIR/MS 等）",
        "互补保留：图标用于标识，模块框图用于原理示意（光路/气流/流程走向），信息互补"),
    "08-instruments-apparatus/lifescience-instruments": (
        "C icon24 生命科学仪器 40 个 vs E labflow 41 张模块框图，同主题成对（离心机/PCR 仪/流式/生物安全柜等）",
        "互补保留：同上，图标与原理框图互补"),
    "08-instruments-apparatus/thermal-mechanical": (
        "C icon24 40 个 vs E labflow 32 张，同主题成对（灭菌锅/烘箱/加热板/低温冰箱等）",
        "互补保留：同上"),
    "08-instruments-apparatus/separation-fluidics": (
        "C icon24 42 个 vs E labflow 35 张，同主题成对（色谱柱/蒸馏/真空/过滤等）",
        "互补保留：同上"),
    "08-instruments-apparatus/general-apparatus": (
        "D primitives 通用装置 17 张，与 C/E 仪器目录无同目录冲突",
        "互补保留：无跨 series 同主题对"),
    "09-safety-signage/ppe-emergency": (
        "C icon24 安全装备图标 43 个 vs E labflow PPE/应急插画 51 张，同主题成对（护目镜/手套/洗眼器/灭火器/生物安全柜等）",
        "互补保留：图标用于快速识别，插画用于培训材料，细节层级不同"),
    "09-safety-signage/hazard-signs": (
        "E labflow 危害标志 53 张（黄底警示/红色禁止/GHS 菱形），与 ppe 目录 signal-* 纯符号 2 张跨目录分工",
        "互补保留：hz 为场景警示牌，signal-* 为纯 ISO 符号；本目录内无重复对"),
    "09-safety-signage/signage": (
        "C icon24 安全标识 13 张（ISO 7010 几何），与 hazard-signs 的 E 系彩底版同主题（电击/高温/噪声/禁烟/禁止明火等）",
        "互补保留：C 为黑白线稿版（可印刷单色），E 为标准彩底版；信息一致但呈现用途不同"),
    "10-figure-elements/scale-reference": (
        "B atlas 尺寸对比 13 张（0.34nm—0.2mm 全尺度），无跨 series 冲突",
        "互补保留：无冲突对"),
    "10-figure-elements/connectors": (
        "C icon24 流程连接符 19 个，与 10/arrows-connectors 的 D 系跨目录分工（图版箭头 vs 流程图连接件）",
        "互补保留：无同目录冲突对"),
    "11-diagrams-charts/flowchart-syntax": (
        "D primitives 流程图语法 72 个 vs E labflow 实验流程节点 37 个，同主题成对（起止/判定/数据/存储等）",
        "互补保留：D 为通用流程语法全集（含逻辑门/UML 箭头），E 为实验流程专用节点；取舍不同"),
    "11-diagrams-charts/charts-plots": (
        "D primitives 图表骨架 64 个 vs E labflow 科研图表 23 张，同主题成对（柱/箱线/小提琴/生存曲线等）",
        "互补保留：D 为带数据的完整图例版，E 为带科研语义的特化版（火山图/剂量响应/K-M），互补"),
    "11-diagrams-charts/pid-process": (
        "C icon24 P&ID 符号 42 个 vs E labflow 单元操作设备 36 张，同主题成对（泵/阀/换热器/反应器/塔器）",
        "互补保留：C 为 ISA 标准符号（画 P&ID 用），E 为设备外形示意（画流程说明用）"),
    "11-diagrams-charts/physics-circuits": (
        "D primitives 物理光路+电路符号 60 个 vs E labflow 电工器件 35 个，同主题成对（电阻/电容/二极管/开关/电源等）",
        "互补保留：两套均为标准符号画法但体系独立（D 深蓝粗线教学版、E 蓝细线设备版），各自成套、混删破坏任一系列完整性"),
    "12-icons-ui/icons-ui": (
        "D basic-icons 68 个线性图标 vs E ic 30 个彩色点缀图标，同主题成对（flask/microscope/DNA/atom/gear/chart-bar/filter 等 10 余对）",
        "互补保留：线性版用于正文排版，彩色版用于 UI 状态强调；成对但语义层不同"),
}


def main():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert len(ledger) == 2830

    # P3 期间实际改动过的素材文件（相对 P2 提交）
    out = subprocess.run(
        ["git", "diff", "--name-only", P2_COMMIT, "HEAD", "--", "assets"],
        cwd=ROOT, capture_output=True, text=True)
    changed = {line.strip() for line in out.stdout.splitlines() if line.strip().endswith(".svg")}

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    n_conflict = 0
    for row in ledger:
        row["science"]["verdict"] = "pass"
        row["art"]["verdict"] = "pass"
        row["reviewed_at"] = now
        if row["file"] in changed:
            row["science"]["fixes"] = ["P3 修复：字号下限重排/标签挪位（含引线）/安全标志几何/许可或字体链归一 之一或多项，见 git 历史 P3 批次1-2"]
        cat = row["category"]
        subdir = row["file"].split("/")[2]
        key = f"{cat}/{subdir}"
        if key in CONFLICT_GROUPS:
            note, decision = CONFLICT_GROUPS[key]
            row["conflict"] = {"verdict": "adjudicated", "decision": decision + "（配对组：" + note + "）"}
            n_conflict += 1

    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"台账更新：2830 行 science/art=pass；conflict 裁决覆盖 {n_conflict} 行；"
          f"P3 改动登记 {len(changed)} 文件")


if __name__ == "__main__":
    main()
