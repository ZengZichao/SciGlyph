# 贡献指南

## 环境依赖

- python3（标准库即可跑全部闸门；渲染预览另需 cairosvg/Pillow）
- node（jsdom，仅画廊交互测试需要）

## 新增/修改素材

1. 放入对应的 `assets/<大类>/<子目录>/`，命名 `NNN-slug-en.svg`（序号接续，slug 全库唯一、纯 ASCII 小写 kebab）。
2. SVG 硬性要求：零脚本/零外链/零内嵌位图；颜色一律字面 hex；中文渲染文本字体链用
   `'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif`（英文版 Inter,Helvetica,Arial）；
   字号 ≥ 下限（大画布 7、微型图标 4）；标签零重叠、文字不出画。
3. 带中文渲染文本的素材必须同时提交 `.en.svg`（可用 `tools/derive_en_variants.py` 派生后人工润色）。
4. 更新所在子目录 `manifest.json`（name_zh/name_en/tags≥3/series/format/canvas），顶层与类别 manifest 同步计数。
5. 跑 `python3 tools/check_repo.py` 必须全绿。
6. 提交信息一行说明改动范围。

## 闸门明细

`tools/check_repo.py` 校验：目录结构与二级目录数、文件名与全库唯一性、序号连续、manifest 严格字段（含 en 配对）、
SVG 安全（脚本/外链/位图/非字面颜色）、许可元数据、CJK 字体链、字号下限、标签零重叠、文字出画、安全标志旋转对称、zh-en 配对完整。
`tools/legibility.py`、`tools/fix_label_overlap.py --check`、`tools/fix_text_overflow.py`、`tools/check_symbol_symmetry.py`
可单独调用定位问题；`tools/derive_en_variants.py --strict` 校验双语覆盖。
