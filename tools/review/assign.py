# -*- coding: utf-8 -*-
"""把接触表按每 3 页一组切成复核任务，写出 qa/review/assign/agentNN.json。

每个任务包含：负责的 sheet、该 sheet 内全部素材、素材的机器度量与 flag、
以及涉及本组素材的重复签名组。复核规则见 qa/review/RUBRIC.md。
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--prefix", default="agent")
ap.add_argument("--per", type=int, default=3)
ap.add_argument("--suffix", default="")
args = ap.parse_args()
PER = args.per
idx = json.loads((ROOT / "qa/review/sheets-index.json").read_text(encoding="utf-8"))
m = json.loads((ROOT / "qa/review/metrics.json").read_text(encoding="utf-8"))
pf, flags, dups = m["per_file"], m["flags"], m["duplicate_signatures"]
asset_flags = {}
for k, v in flags.items():
    for p in v:
        asset_flags.setdefault(p, []).append(k)
out = ROOT / "qa/review/assign"
out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*.json"):
    f.unlink()
n = 0
for i in range(0, len(idx), PER):
    n += 1
    chunk = idx[i:i + PER]
    assets = [a for s in chunk for a in s["assets"]]
    items = []
    for a in assets:
        d = pf.get(a, {})
        items.append({"file": a, "title": d.get("title", ""), "fill": d.get("fill"),
                      "bbox": d.get("bbox"), "off": [d.get("offx"), d.get("offy")],
                      "n_text": d.get("n_text"), "min_fs": d.get("min_fs"),
                      "n_colors": d.get("n_colors"), "flags": asset_flags.get(a, [])})
    (out / f"{args.prefix}{n:02d}{args.suffix}.json").write_text(json.dumps(
        {"agent": f"{args.prefix}{n:02d}{args.suffix}", "sheets": [s["sheet"] for s in chunk],
         "titles": [s["title"] for s in chunk], "n_assets": len(assets),
         "assets": items,
         "duplicate_groups_touching": [v for v in dups.values()
                                       if any(a in assets for a in v)]},
        ensure_ascii=False, indent=1), encoding="utf-8")
print(f"agents={n} assets={sum(len(s['assets']) for s in idx)}")
