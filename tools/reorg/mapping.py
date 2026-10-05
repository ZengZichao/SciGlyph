# -*- coding: utf-8 -*-
"""重组映射定义：65 个源分类 -> 12 大类 / 44 个二级目录。

series: classic(A) atlas(B) icon24(C) primitives(D) labflow(E)
format: illustration / diagram / icon
"""

# 12 大类（编号, 目录名, 中文名, 英文名）
CATEGORIES = [
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

# 二级目录：key -> (大类编号, subdir, 中文名, 英文名)
SUBDIRS = {
    # 01
    "morphology-arrangement": ("01", "morphology-arrangement", "形态与排列", "Morphology & Arrangement"),
    "cell-structures":        ("01", "cell-structures", "细胞结构", "Cell Structures"),
    "cell-envelope":          ("01", "cell-envelope", "细胞包膜", "Cell Envelope"),
    "appendages-motility":    ("01", "appendages-motility", "附属结构与运动", "Appendages & Motility"),
    "archaea":                ("01", "archaea", "古菌", "Archaea"),
    "viruses-phages":         ("01", "viruses-phages", "病毒与噬菌体", "Viruses & Phages"),
    "eukaryotic-cells-organelles": ("01", "eukaryotic-cells-organelles", "真核细胞与细胞器", "Eukaryotic Cells & Organelles"),
    # 02
    "genes-mge":              ("02", "genes-mge", "基因与移动遗传元件", "Genes & MGE"),
    "sequence-graphics":      ("02", "sequence-graphics", "序列图形", "Sequence Graphics"),
    "population-genomics":    ("02", "population-genomics", "群体基因组", "Population Genomics"),
    "comparative-pan":        ("02", "comparative-pan", "比较基因组与泛基因组", "Comparative & Pan-genomics"),
    "molecular-ecology":      ("02", "molecular-ecology", "分子生态", "Molecular Ecology"),
    "mol-structures":         ("02", "mol-structures", "分子结构", "Molecular Structures"),
    "omics-charts":           ("02", "omics-charts", "组学数据图", "Omics Charts"),
    # 03
    "metabolism":             ("03", "metabolism", "代谢", "Metabolism"),
    "phenotype":              ("03", "phenotype", "生理表型", "Physiological Phenotype"),
    # 04
    "tree-skeletons":         ("04", "tree-skeletons", "树骨架", "Tree Skeletons"),
    "tree-annotation":        ("04", "tree-annotation", "树注释", "Tree Annotation"),
    "evolution-process":      ("04", "evolution-process", "演化过程", "Evolutionary Process"),
    "nomenclature":           ("04", "nomenclature", "命名法规", "Nomenclature"),
    # 05
    "habitats":               ("05", "habitats", "生境", "Habitats"),
    "interactions":           ("05", "interactions", "互作与物质流", "Interactions & Matter Flow"),
    "biotech-applications":   ("05", "biotech-applications", "生物技术应用", "Biotech Applications"),
    # 06
    "culture-biochem":        ("06", "culture-biochem", "培养与生化鉴定", "Culture & Biochemical Tests"),
    "analysis-pipelines":     ("06", "analysis-pipelines", "分析流程", "Analysis Pipelines"),
    "omics-workflow":         ("06", "omics-workflow", "组学工作流", "Omics Workflows"),
    "microscopy-detection":   ("06", "microscopy-detection", "镜检与检测技术", "Microscopy & Detection"),
    # 07
    "glassware":              ("07", "glassware", "玻璃器皿", "Glassware"),
    "storage-consumables":    ("07", "storage-consumables", "储存与耗材", "Storage & Consumables"),
    "hardware-tools":         ("07", "hardware-tools", "支架与工具", "Hardware & Tools"),
    "general-labware":        ("07", "general-labware", "通用器材", "General Labware"),
    # 08
    "analytical-instruments": ("08", "analytical-instruments", "分析仪器", "Analytical Instruments"),
    "lifescience-instruments":("08", "lifescience-instruments", "生命科学仪器", "Life-science Instruments"),
    "thermal-mechanical":     ("08", "thermal-mechanical", "热学与机械", "Thermal & Mechanical"),
    "separation-fluidics":    ("08", "separation-fluidics", "分离与流控", "Separation & Fluidics"),
    "liquid-handling":        ("08", "liquid-handling", "移液与液体处理", "Liquid Handling"),
    "electrical-equipment":   ("08", "electrical-equipment", "电气器材", "Electrical Equipment"),
    "monitoring-sensors":     ("08", "monitoring-sensors", "监测与传感", "Monitoring & Sensors"),
    "general-apparatus":      ("08", "general-apparatus", "通用装置", "General Apparatus"),
    # 09
    "hazard-signs":           ("09", "hazard-signs", "危害警示标志", "Hazard Signs"),
    "ppe-emergency":          ("09", "ppe-emergency", "防护与应急", "PPE & Emergency"),
    "personnel-behavior":     ("09", "personnel-behavior", "人员行为", "Personnel Behavior"),
    "signage":                ("09", "signage", "安全标识", "Safety Signage"),
    # 10
    "scale-reference":        ("10", "scale-reference", "比例与尺度参照", "Scale Reference"),
    "figure-layout":          ("10", "figure-layout", "图版布局", "Figure Layout"),
    "arrows-connectors":      ("10", "arrows-connectors", "箭头与连接件", "Arrows & Connectors"),
    "geometry-math":          ("10", "geometry-math", "几何与数学", "Geometry & Math"),
    "tables-frames":          ("10", "tables-frames", "表格与框线", "Tables & Frames"),
    "labels-tags":            ("10", "labels-tags", "标签与标牌", "Labels & Tags"),
    "connectors":             ("10", "connectors", "流程连接符", "Flow Connectors"),
    # 11
    "flowchart-syntax":       ("11", "flowchart-syntax", "流程图语法", "Flowchart Syntax"),
    "diagrams-uml":           ("11", "diagrams-uml", "软件图与 UML", "Software Diagrams & UML"),
    "charts-plots":           ("11", "charts-plots", "图表与绘图", "Charts & Plots"),
    "pid-process":            ("11", "pid-process", "工艺流程与单元操作", "P&ID & Unit Operations"),
    "physics-circuits":       ("11", "physics-circuits", "物理光路与电路", "Physics Optics & Circuits"),
    # 12
    "icons-ui":               ("12", "icons-ui", "图标", "Icons"),
}

# 源分类整类映射：源key -> (subdir, format)
# series 由来源子库决定：A=classic B=atlas C=icon24 D=primitives E=labflow
WHOLE_MAP = {
    # A
    ("A", "01-morphology"):  ("morphology-arrangement", "illustration"),
    ("A", "02-structures"):  ("cell-structures", "illustration"),
    ("A", "03-phenotype"):   ("phenotype", "illustration"),
    ("A", "04-phylo"):       ("tree-skeletons", "diagram"),
    # B
    ("B", "morphology"):         ("morphology-arrangement", "illustration"),
    ("B", "cell-envelope"):      ("cell-envelope", "illustration"),
    ("B", "appendages"):         ("appendages-motility", "illustration"),
    ("B", "archaea"):            ("archaea", "illustration"),
    ("B", "virology"):           ("viruses-phages", "illustration"),
    ("B", "genes-mge"):          ("genes-mge", "diagram"),
    ("B", "sequence-graphics"):  ("sequence-graphics", "diagram"),
    ("B", "population-genomics"):("population-genomics", "diagram"),
    ("B", "comparative"):        ("comparative-pan", "diagram"),
    ("B", "molecular-ecology"):  ("molecular-ecology", "diagram"),
    ("B", "metabolism"):         ("metabolism", "illustration"),
    ("B", "trees"):              ("tree-skeletons", "diagram"),
    ("B", "tree-decor"):         ("tree-annotation", "diagram"),
    ("B", "evolution-process"):  ("evolution-process", "diagram"),
    ("B", "nomenclature"):       ("nomenclature", "diagram"),
    ("B", "environments"):       ("habitats", "illustration"),
    ("B", "eco-interactions"):   ("interactions", "illustration"),
    ("B", "methods"):            ("culture-biochem", "diagram"),
    ("B", "workflow"):           ("analysis-pipelines", "diagram"),
    ("B", "figure-layout"):      ("figure-layout", "diagram"),
    ("B", "microscopy-scale"):   ("microscopy-detection", "diagram"),  # 逐张判覆盖
    # C
    ("C", "glassware"):          ("glassware", "icon"),
    ("C", "hardware"):           ("hardware-tools", "icon"),
    ("C", "instruments"):        ("analytical-instruments", "icon"),
    ("C", "lifescience"):        ("lifescience-instruments", "icon"),
    ("C", "thermal-mechanical"): ("thermal-mechanical", "icon"),
    ("C", "separation-fluid"):   ("separation-fluidics", "icon"),
    ("C", "electrical"):         ("electrical-equipment", "icon"),
    ("C", "safety"):             ("ppe-emergency", "icon"),
    ("C", "process"):            ("pid-process", "icon"),
    ("C", "signage-flow"):       ("connectors", "icon"),  # 逐张判覆盖
    # D
    ("D", "arrows-connectors"):  ("arrows-connectors", "diagram"),
    ("D", "geometry-math"):      ("geometry-math", "diagram"),
    ("D", "tables-frames"):      ("tables-frames", "diagram"),
    ("D", "flowchart-logic"):    ("flowchart-syntax", "diagram"),
    ("D", "diagrams-sw-uml"):    ("diagrams-uml", "diagram"),
    ("D", "charts-plots"):       ("charts-plots", "diagram"),
    ("D", "physics-electronics"):("physics-circuits", "diagram"),
    ("D", "basic-icons-ui"):     ("icons-ui", "icon"),
    ("D", "lab-equipment"):      ("general-labware", "illustration"),  # 逐张判覆盖
    ("D", "natural-sciences"):   ("eukaryotic-cells-organelles", "illustration"),  # 逐张判覆盖
    # E（双字母前缀为源分类）
    ("E", "an"): ("analytical-instruments", "illustration"),
    ("E", "ch"): ("charts-plots", "diagram"),
    ("E", "cs"): ("storage-consumables", "illustration"),
    ("E", "el"): ("physics-circuits", "diagram"),
    ("E", "en"): ("monitoring-sensors", "illustration"),
    ("E", "gl"): ("glassware", "illustration"),
    ("E", "hc"): ("thermal-mechanical", "illustration"),
    ("E", "hz"): ("hazard-signs", "illustration"),
    ("E", "ic"): ("icons-ui", "icon"),
    ("E", "lb"): ("labels-tags", "illustration"),
    ("E", "lh"): ("liquid-handling", "illustration"),
    ("E", "ls"): ("lifescience-instruments", "illustration"),
    ("E", "mt"): ("monitoring-sensors", "illustration"),
    ("E", "pf"): ("flowchart-syntax", "diagram"),
    ("E", "pp"): ("personnel-behavior", "illustration"),
    ("E", "sf"): ("ppe-emergency", "illustration"),
    ("E", "sp"): ("separation-fluidics", "illustration"),
    ("E", "st"): ("storage-consumables", "illustration"),
    ("E", "uo"): ("pid-process", "diagram"),
}

SERIES = {"A": "classic", "B": "atlas", "C": "icon24", "D": "primitives", "E": "labflow"}


def a05_dest(fname: str):
    """A 05-eco-seq 逐张判：文件名序号决定去向。"""
    n = int(fname.split("-")[0])
    if n <= 16:
        return ("habitats", "illustration")
    if n <= 26:
        return ("omics-workflow", "diagram")
    if n <= 30:
        return ("omics-charts", "diagram")
    return ("biotech-applications", "diagram")


def b_micro_dest(fname: str):
    """B microscopy-scale 逐张判：21-33 号为尺寸对比/比例尺 -> scale-reference；其余为观测检测技术。"""
    stem = fname[:-4] if fname.endswith(".svg") else fname
    n = int(stem.split("_")[0])
    if 21 <= n <= 33:
        return ("scale-reference", "diagram")
    return ("microscopy-detection", "diagram")


def c_sign_dest(fname: str):
    """C signage-flow 逐张判：sign-* 安全标志 -> 09/signage；其余连接符/图版构件 -> 10/connectors。"""
    if fname.startswith("sign-"):
        return ("signage", "icon")
    return ("connectors", "icon")


def d_ns_dest(fname: str):
    """D natural-sciences 逐张判。
    分子结构（核酸 01-08、膜 20-25、生化分子 26-38）-> 02/mol-structures；
    细菌形态 39-41 -> 01/morphology-arrangement；
    病毒/噬菌体 42-44、朊粒 49 -> 01/viruses-phages；
    真核细胞/细胞器/组织 09-19、45-48、50-59、70 -> 01/eukaryotic-cells-organelles；
    食物链/物质循环/地质过程 60-69 -> 05/interactions；
    蒸腾/光合 71-72 -> 03/metabolism。
    """
    n = int(fname.split("-")[1])
    if n <= 8:
        return ("mol-structures", "illustration")
    if n <= 19:
        return ("eukaryotic-cells-organelles", "illustration")
    if 20 <= n <= 25:
        return ("mol-structures", "illustration")
    if 26 <= n <= 38:
        return ("mol-structures", "illustration")
    if 39 <= n <= 41:
        return ("morphology-arrangement", "illustration")
    if 42 <= n <= 44:
        return ("viruses-phages", "illustration")
    if 45 <= n <= 48:
        return ("eukaryotic-cells-organelles", "illustration")
    if n == 49:
        return ("viruses-phages", "illustration")
    if 50 <= n <= 59:
        return ("eukaryotic-cells-organelles", "illustration")
    if 60 <= n <= 69:
        return ("interactions", "illustration")
    if n == 70:
        return ("eukaryotic-cells-organelles", "illustration")
    return ("metabolism", "illustration")


def d_lb_dest(fname: str):
    """D lab-equipment 逐张判：器皿/耗材/手持支架工具 -> 07/general-labware；
    带动力/电子/柜式大型装置 -> 08/general-apparatus。
    """
    apparatus = {35, 38, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60}
    n = int(fname.split("-")[1])
    if n in apparatus:
        return ("general-apparatus", "illustration")
    return ("general-labware", "illustration")


# 逐张判函数表
SPLIT_RULES = {
    ("A", "05-eco-seq"): a05_dest,
    ("B", "microscopy-scale"): b_micro_dest,
    ("C", "signage-flow"): c_sign_dest,
    ("D", "natural-sciences"): d_ns_dest,
    ("D", "lab-equipment"): d_lb_dest,
}
