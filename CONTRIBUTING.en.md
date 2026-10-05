# Contributing

## Prerequisites

- python3 (the standard library runs every gate; cairosvg/Pillow only for preview rendering)
- node (jsdom, only for gallery interaction tests)

## Adding or editing assets

1. Place files in `assets/<category>/<subfolder>/` named `NNN-slug-en.svg` (continuing numbers; slug globally unique, lowercase ASCII kebab-case).
2. Hard SVG requirements: no scripts, no external references, no embedded bitmaps; literal hex colors only; rendered Chinese text uses
   `'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif` (English variants use Inter,Helvetica,Arial);
   font size at or above the floor (7 for large canvases, 4 for micro icons); zero label overlap; no text outside the viewBox.
3. Assets with rendered Chinese text must ship an `.en.svg` variant (derive with `tools/derive_en_variants.py`, then polish).
4. Update the subfolder `manifest.json` (name_zh/name_en/tags>=3/series/format/canvas); keep category and root manifests in sync.
5. `python3 tools/check_repo.py` must pass fully.
6. One-line commit messages describing the scope.

## Gate details

`tools/check_repo.py` validates: directory structure and subfolder counts, file names and global uniqueness, sequential numbering,
strict manifest fields (including en pairing), SVG safety (scripts/external refs/bitmaps/non-literal colors), license metadata,
CJK font stacks, minimum type size, zero label overlap, text overflow, safety-symbol rotational symmetry, zh/en pairing.
`tools/legibility.py`, `tools/fix_label_overlap.py --check`, `tools/fix_text_overflow.py` and `tools/check_symbol_symmetry.py`
can be run individually to locate issues; `tools/derive_en_variants.py --strict` verifies bilingual coverage.
