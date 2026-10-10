# -*- coding: utf-8 -*-
"""把各复核 agent 登记在 findings 的 `## MANIFEST-CHANGES` 落盘到子目录 manifest.json。

约定（见 qa/review/RUBRIC.md C 节）：agent 不直接改 manifest，改为在此登记
  `- assets/<大类>/<子目录>/<文件>.svg | name_en: 旧 -> 新 | desc: 旧 -> 新`
本脚本按 mtime 顺序读取（后写的结论覆盖先写的），只接受 name_zh / name_en / desc /
tags / format / canvas 六个字段，并清洗掉括号里的说明性文字。

用法：
  python tools/review/apply_manifest_changes.py --dry     # 只看将要改什么
  python tools/review/apply_manifest_changes.py           # 落盘
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("name_zh", "name_en", "desc", "tags", "format", "canvas")
PATH_RE = re.compile(r"assets/[^\s`,|()'\"：]+\.svg")
SEG_RE = re.compile(r"(name_zh|name_en|desc|tags|format|canvas)\s*[:：]\s*(.*)$", re.S)
NOISE = re.compile(r"[（(](?:理由|重画|承|待|若|画面|现|本组|NEEDS|登记|已|需|与\s*0|第一轮|后改)[^）)]*[）)]")
# 说明性/未定稿的值一律不落盘
META = re.compile(r"不变|建议|无需|请主控|需人工|待定|作废|※|已同步|未落盘|二选一|待重画|按\s*diagram"
                  r"|末尾追加|补注|需补|拟改|合并|待主控|拟改|若后续")
FORMAT_OK = {"illustration", "diagram", "icon"}
# 值里混入的说明性尾巴，从这些词起截断
TAIL = re.compile(r"[。.\s]*（?(?:理由|※|建议|需同步|待主控|现画面|画面已|本轮|tags 内|desc 已|name_zh|与\s*\d{3}\b)[^）]*）?")


def clean(v: str) -> str:
    v = v.split("|")[0].strip()
    v = NOISE.sub("", v)
    v = TAIL.split(v, 1)[0] if TAIL.search(v) else v
    v = re.sub(r"^(?:\.\.\.|…)+", "", v.strip())
    v = v.strip().strip('"').strip("'").strip("“”").strip()
    v = re.sub(r"[\"“”‘’'」」]+$", "", v).strip()
    v = re.sub(r"\s*->\s*$", "", v)
    return v.strip()


def parse_value(seg: str):
    """'旧 -> 新' 取新；没有箭头则整段视为新值。"""
    if "->" in seg:
        seg = seg.split("->", 1)[1]
    elif "→" in seg:
        seg = seg.split("→", 1)[1]
    return clean(seg)


meta_skipped = []


def collect():
    out = {}
    files = sorted((ROOT / "qa/review/findings").glob("*.md"),
                   key=lambda p: (p.stat().st_mtime, p.name))
    for f in files:
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r"## MANIFEST-CHANGES(.*?)(?=\n## |\Z)", txt, re.S):
            for line in m.group(1).splitlines():
                s = line.strip()
                if not s.startswith("-"):
                    continue
                pm = PATH_RE.search(s)
                if not pm:
                    continue
                rel = pm.group(0)
                if not (ROOT / rel).exists():
                    continue
                for seg in s.split("|")[1:]:
                    sm = SEG_RE.search(seg.strip())
                    if not sm:
                        continue
                    field, val = sm.group(1), parse_value(sm.group(2))
                    if not val or len(val) > 400:
                        continue
                    if META.search(val):
                        out.pop((rel, field), None)
                        meta_skipped.append((rel, field, val[:50]))
                        continue
                    if field == "format" and val not in FORMAT_OK:
                        meta_skipped.append((rel, field, "非法 format 值，跳过"))
                        continue
                    if field in ("name_zh", "name_en"):
                        val = re.sub(r"[（(][^）)]{6,}[）)]\s*$", "", val).strip()
                    out[(rel, field)] = (val, f.name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    changes = collect()
    by_manifest = {}
    for (rel, field), (val, src) in changes.items():
        sub = (ROOT / rel).parent
        by_manifest.setdefault(sub, []).append((Path(rel).name, field, val, src))

    applied, skipped, touched = 0, [], 0
    for sub, items in sorted(by_manifest.items()):
        mp = sub / "manifest.json"
        if not mp.exists():
            skipped += [(str(mp), "no manifest")]
            continue
        data = json.loads(mp.read_text(encoding="utf-8"))
        idx = {it.get("file"): it for it in data.get("items", [])}
        dirty = False
        for fname, field, val, src in items:
            it = idx.get(fname)
            if it is None:
                base = re.sub(r"\.en\.svg$", ".svg", fname)
                it = idx.get(base)
            if it is None:
                skipped += [(f"{sub.name}/{fname}", "not in manifest")]
                continue
            if field == "tags":
                skipped += [(f"{sub.name}/{fname}", "tags 需人工定夺")]
                continue
            old = it.get(field)
            if old == val:
                continue
            it[field] = val
            dirty = True
            applied += 1
            print(f"  {field:8s} {sub.name}/{fname}: {str(old)[:40]!r} -> {val[:60]!r}  [{src}]")
        if dirty and not args.dry:
            mp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8", newline="\n")
            touched += 1
    print(("DRY-RUN 将" if args.dry else "已") + f"落字段 {applied} 个，改写 manifest {touched} 份")
    if meta_skipped:
        print("")
        print(f"未定稿/说明性条目 {len(meta_skipped)} 条未落盘：")
        for rel, field, why in meta_skipped[:20]:
            print(f"    {field} {rel} — {why}")
    if skipped:
        print("跳过：")
        for k, why in skipped:
            print("   ", k, "—", why)


if __name__ == "__main__":
    main()
