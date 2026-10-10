# SciGlyph — Scientific Illustration Asset Library (SVG, v1.0.0)

**SciGlyph** is an open SVG library for scientific figure-making: **2830 assets** (plus 260 `.en.svg` English-text variants), organized into 12 discipline categories, five visual series and three formats (illustration / diagram / icon).

> ⚠️ **AI-generated notice**: every asset in this library was generated with the assistance of AI models, followed by human review and automated QA checks. Errors may still remain — **before formal use (especially publication), verify the scientific accuracy of each figure against authoritative sources.**

## Preview

![Overview](preview/sciglyph-overview.png)

![Five visual series](preview/sciglyph-series.png)

![Glassware, instruments and safety](preview/sciglyph-lab.png)

![Figure elements, charts and icons](preview/sciglyph-figures.png)

- License: assets **CC BY 4.0** (© ZengZichao); tooling and pages **MIT**.
- Chinese documentation: [README.md](README.md); series guide: [README-SERIES.en.md](README-SERIES.en.md) / [README-SERIES.md](README-SERIES.md).
- Browse: open `index.html` from the repo root (works offline, with zh/en toggle and light/dark themes).
- Online gallery: pushed to GitHub and published automatically via Pages (see [DEPLOY.en.md](DEPLOY.en.md)).
- Citation: see [CITATION.cff](CITATION.cff) and [NOTICE](NOTICE).

## 12 categories

| ID | Category | Assets |
|---|---|---|
| 01-cells-microbes | Cells & Microbes: Morphology and Structure | 295 |
| 02-genetics-omics | Genetics & Omics | 233 |
| 03-metabolism-phenotype | Metabolism & Physiological Phenotype | 105 |
| 04-phylogeny-evolution | Phylogeny & Evolution | 201 |
| 05-ecology-biotech | Ecology, Habitats & Applications | 121 |
| 06-lab-methods | Lab Methods & Workflows | 140 |
| 07-glassware-consumables | Glassware, Consumables & General Labware | 244 |
| 08-instruments-apparatus | Instruments & Apparatus | 440 |
| 09-safety-signage | Safety & Signage | 191 |
| 10-figure-elements | Figure Elements | 325 |
| 11-diagrams-charts | Diagrams, Flows & Charts | 437 |
| 12-icons-ui | Icons & UI | 98 |
| | **Total** | **2830** |

Format mix: illustration 1102 · diagram 1224 · icon 504.

## Conventions

- File names follow `NNN-slug-en.svg` (3-digit number + globally unique kebab-case English slug); assets with rendered Chinese text ship with a matching `.en.svg` English variant.
- Every asset: no scripts, no external references, no embedded bitmaps; literal hex colors; Chinese text uses a CJK-fallback font stack.
- Each file carries `data-license="CC-BY-4.0" data-copyright="ZengZichao"`; every manifest entry includes license/license_uri/attribution.
- Quality gate: `python3 tools/check_repo.py` (structure, naming, manifest, SVG safety, licensing, font stacks, minimum type size, zero label overlap, no text overflow, renderability, safety-symbol symmetry, zh/en pairing); `python3 tools/check_site.py` keeps the gallery and the assets in sync.

## Layout

```
绘图素材库/
├── README.md / README.en.md / README-SERIES.md / README-SERIES.en.md
├── LICENSE (MIT) / LICENSE-ASSETS (CC BY 4.0) / NOTICE / CITATION.cff
├── index.html            # single gallery (search/filter/zh-en/light-dark)
├── preview/              # consolidated preview images (sciglyph-*.png)
├── assets/01..12-*/      # 12 categories, each with subfolders and a SPEC
└── tools/                # QA and build tooling
```