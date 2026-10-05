#!/usr/bin/env python3
"""字号下限 + 标签重叠的人工级自动重排（工具）。

对每个低于下限的 <text>：
  1. 字号放大到下限；
  2. 螺旋搜索画布内的空闲位置（放大后的盒子不与任何文字盒相交、不出画布），
     优先最小位移；位移超过阈值时补一条细引线（原锚点 → 新位置）；
  3. 找不到位置时保留原状并登记（留人工删减/改写）。

用法：
  python3 tools/fix_labels_manual.py                 # 处理全部并落盘
  python3 tools/fix_labels_manual.py --dry           # 只报告
  python3 tools/fix_labels_manual.py --filter 01-cells
退出码：0；残留清单打印到 stdout。
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import legibility as leg  # noqa: E402
import fix_label_overlap as flo  # noqa: E402
from svgtext import _mat_mul, _to_abs, parse_transform, text_local_bbox  # noqa: E402

LEADER_COLOR = "#5A6B7B"


def mat_inv(m):
    a, b, c, d, e, f = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    return (d / det, -b / det, -c / det, a / det,
            (c * f - d * e) / det, (b * e - a * f) / det)


def overlap_fix_pass(p: Path, max_iter=6):
    """用 flo 的变换感知盒模型迭代消解标签重叠：每次把对中"后出现"的标签
    螺旋挪到空闲位置（保持字号与内容，只改 x/y，可补引线）。返回剩余对数。"""
    for _round in range(max_iter):
        raw = p.read_text(encoding="utf-8")
        info = flo.analyze(raw)
        if not info:
            return -1
        pairs, boxes, vw, vh = info
        if not pairs:
            return 0
        # 只处理一批（每轮一个文件一批），避免多次改写相互干扰
        j_target = max(j for _i, j in pairs)
        content, el, box, m, fs = boxes[j_target]
        a_, b_, c_, d_, _e2, _f2 = m
        if abs(c_) > 1e-3 or abs(b_) > 1e-3:
            continue  # 旋转标签不动，留人工
        inv = mat_inv(m)
        if inv is None:
            continue
        # 其余盒为障碍
        obstacles = [boxes[k][2] for k in range(len(boxes)) if k != j_target]
        w = box[2] - box[0]
        h = box[3] - box[1]
        placed = None
        for cx, cy in spiral_positions(vw or 100, vh or 100, w, h, box[0], box[1]):
            nb = clamp_box(cx, cy, w, h, vw or 100, vh or 100)
            if any(flo._overlap(nb, o) for o in obstacles):
                continue
            placed = nb
            break
        if placed is None:
            continue
        # 绝对目标盒 → 局部坐标平移
        ldx, ldy = None, None
        l0 = flo.text_local_bbox(el, content, fs)
        abs0 = _to_abs(l0, m)
        tl_desired = (placed[0], placed[1])
        lx, ly = (inv[0] * tl_desired[0] + inv[2] * tl_desired[1] + inv[4],
                  inv[1] * tl_desired[0] + inv[3] * tl_desired[1] + inv[5])
        ldx, ldy = lx - l0[0], ly - l0[1]
        new_x = float(el.get("x", "0")) + ldx
        new_y = float(el.get("y", "0")) + ldy
        # 在源文本中定位该 <text>（按内容+旧坐标匹配）
        pat = re.compile(r'<text\b[^>]*\bx="([^"]+)"[^>]*\by="([^"]+)"[^>]*>.*?</text>', re.S)
        replaced = False

        def sub(mm):
            nonlocal replaced
            if replaced:
                return mm.group(0)
            try:
                mx, my = float(mm.group(1)), float(mm.group(2))
            except ValueError:
                return mm.group(0)
            if abs(mx - float(el.get("x", "0"))) < 1e-6 and abs(my - float(el.get("y", "0"))) < 1e-6 \
                    and re.sub(r"<[^>]+>", "", mm.group(0)).strip() == content:
                replaced = True
                tag = mm.group(0)
                dist = math.hypot(placed[0] - box[0], placed[1] - box[1])
                tag = re.sub(r'([\s])x="[^"]*"', rf'\g<1>x="{round(new_x, 2)}"', tag, count=1)
                tag = re.sub(r'([\s])y="[^"]*"', rf'\g<1>y="{round(new_y, 2)}"', tag, count=1)
                if dist > 6:
                    ox, oy = box[0] + 1, (box[1] + box[3]) / 2
                    lx1 = round(min(max(placed[0], 1), (vw or 100) - 1), 2)
                    ly1 = round(placed[1] + 1, 2)
                    leader = (f'<line x1="{round(ox, 2)}" y1="{round(oy, 2)}" x2="{lx1}" y2="{ly1}" '
                              f'stroke="{LEADER_COLOR}" stroke-width="0.5" stroke-dasharray="1.5,1.2"/>')
                    return tag + leader
                return tag
            return mm.group(0)

        new_raw = pat.sub(sub, raw, count=0)
        if replaced:
            p.write_text(new_raw, encoding="utf-8")
        else:
            return len(pairs)
    info = flo.analyze(p.read_text(encoding="utf-8"))
    return len(info[0]) if info else -1


def spiral_positions(cw, ch, w, h, cx, cy, step=2.0, rings=40):
    """从 (cx,cy) 螺旋外扩的候选锚点（盒子左上角），夹在画布内。"""
    yield cx, cy
    for ring in range(1, rings + 1):
        r = step * ring
        n = max(8, int(2 * math.pi * r / step))
        for k in range(n):
            a = 2 * math.pi * k / n
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a) * 0.7
            x0 = min(max(x, 0.5), max(0.5, cw - w - 0.5))
            y0 = min(max(y, 0.5), max(0.5, ch - h - 0.5))
            yield x0, y0


def clamp_box(x0, y0, w, h, vw, vh):
    x0 = min(max(x0, 0.5), max(0.5, vw - w - 0.5))
    y0 = min(max(y0, 0.5), max(0.5, vh - h - 0.5))
    return (x0, y0, x0 + w, y0 + h)


def collect(raw, floor):
    items = []
    for m in leg.TEXT_RE.finditer(raw):
        tag = m.group(0)
        a = dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]))
        if "font-size" not in a:
            continue
        try:
            fs = float(a["font-size"])
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
        except ValueError:
            continue
        content = re.sub(r"<[^>]+>", "", tag)
        content = re.sub(r"^.*?>", "", content, count=1, flags=re.S)
        use = max(fs, floor)
        w = leg.measure(content, use)
        anchor = a.get("text-anchor", "start")
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        box = (x0, y - use * 0.8, x0 + w, y + use * 0.2)
        items.append({"span": (m.start(), m.end()), "tag": tag, "content": content,
                      "x": x, "y": y, "fs": fs, "use": use, "w": w, "box": box,
                      "anchor": anchor, "below": fs < floor})
    return items


def build_new_tag(it, nb, floor, dist, vw):
    x0, y0, _x1, _y1 = nb
    a = it["anchor"]
    new_x = x0 + (it["w"] / 2 if a == "middle" else it["w"] if a == "end" else 0)
    new_y = y0 + it["use"] * 0.8
    tag = it["tag"].replace(f'font-size="{leg.a_num(it["fs"])}"',
                            f'font-size="{leg.a_num(floor)}"', 1)
    if re.search(r'[\s]x="', tag):
        tag = re.sub(r'([\s])x="[^"]*"', rf'\g<1>x="{round(new_x, 2)}"', tag, count=1)
    else:
        tag = tag.replace("<text", f'<text x="{round(new_x, 2)}"', 1)
    if re.search(r'[\s]y="', tag):
        tag = re.sub(r'([\s])y="[^"]*"', rf'\g<1>y="{round(new_y, 2)}"', tag, count=1)
    else:
        tag = tag.replace("<text", f'<text y="{round(new_y, 2)}"', 1)
    leader = ""
    if dist > 6:
        ox, oy = it["x"], it["y"]
        lx1 = round(min(max(new_x, 1), vw - 1), 2)
        ly1 = round(new_y - floor * 0.3, 2)
        leader = (f'<line x1="{round(ox, 2)}" y1="{round(oy - floor * 0.3, 2)}" '
                  f'x2="{lx1}" y2="{ly1}" stroke="{LEADER_COLOR}" stroke-width="0.5" '
                  f'stroke-dasharray="1.5,1.2"/>')
    return leader + tag


def process_file(p: Path, fix=True):
    raw = p.read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', raw)
    if not vb:
        return [], []
    _vx, _vy, vw, vh = [float(v) for v in vb.group(1).replace(",", " ").split()]
    floor = leg.floor_for(max(vw, vh))
    items = collect(raw, floor)
    below_items = [t for t in items if t["below"]]
    if not below_items:
        return [], []
    obstacles = [t["box"] for t in items if not t["below"]]
    edits, stuck = [], []
    for it in below_items:
        placed = False
        start = (it["box"][0], it["box"][1])
        for cx, cy in spiral_positions(vw, vh, it["w"], it["use"], start[0], start[1]):
            nb = clamp_box(cx, cy, it["w"], it["use"], vw, vh)
            if any(leg.overlap(nb, o) for o in obstacles):
                continue
            if any(leg.overlap(nb, e["nb"]) for e in edits):
                continue
            dist = math.hypot(nb[0] - start[0], nb[1] - start[1])
            edits.append({"it": it, "nb": nb, "dist": dist})
            obstacles.append(nb)
            stuck_note = None
            placed = True
            break
        if not placed:
            stuck.append((it["content"][:24], it["fs"], floor))
    if fix and edits:
        tmp = raw
        marks = []
        for idx, e in enumerate(sorted(edits, key=lambda e: -e["it"]["span"][0])):
            s0, s1 = e["it"]["span"]
            token = f"<!--XL{idx}-->"
            tmp = tmp[:s0] + token + tmp[s1:]
            marks.append((token, e))
        for token, e in marks:
            tmp = tmp.replace(token, build_new_tag(e["it"], e["nb"], floor, e["dist"], vw))
        p.write_text(tmp, encoding="utf-8")
    return [(e["it"]["content"][:20], round(e["dist"], 1)) for e in edits], stuck


def redistribute_pass(p: Path):
    """残留重叠的针对性策略：
    (a) 同一水平行的多个重叠标签 → 在其原有跨度内等距重排 x；
    (b) 纵向堆叠的一对 → 垂直推开到不重叠。
    返回处理的对数（0 = 未变化）。"""
    raw = p.read_text(encoding="utf-8")
    info = flo.analyze(raw)
    if not info:
        return 0
    pairs, boxes, vw, vh = info
    if not pairs:
        return 0
    vw = vw or 100
    vh = vh or 100
    n_pairs = len(pairs)
    # 分组：连通分量
    adj = {}
    for i, j in pairs:
        adj.setdefault(i, set()).add(j)
        adj.setdefault(j, set()).add(i)
    seen, groups = set(), []
    for k in list(adj):
        if k in seen:
            continue
        stack, comp = [k], set()
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            seen.add(u)
            stack.extend(adj[u] - comp)
        groups.append(sorted(comp))
    # 判定行/列
    edits = []
    for comp in groups:
        bs = [boxes[k] for k in comp]
        ycs = sorted((b[2][1] + b[2][3]) / 2 for b in bs)
        row_like = (max(ycs) - min(ycs)) <= max(2.5, 0.35 * max((b[2][3] - b[2][1]) for b in bs))
        if row_like and len(comp) >= 2:
            # 按内容宽度排序后等距铺开
            order = sorted(comp, key=lambda k: boxes[k][2][0])
            total_w = sum(boxes[k][2][2] - boxes[k][2][0] for k in order)
            x_start = min(boxes[k][2][0] for k in order)
            x_end = max(boxes[k][2][2] for k in order)
            span = max(x_end - x_start, total_w + 2.0 * (len(order) - 1))
            gap = (span - total_w) / (len(order) - 1) if len(order) > 1 else 0
            if gap <= 0.2:
                # 跨度不够：整体扩到画布内最大可用宽度
                x_start = max(1.0, min(x_start, vw - span - 1.0))
            cur = x_start
            yc = sum((boxes[k][2][1] + boxes[k][2][3]) / 2 for k in order) / len(order)
            for k in order:
                b = boxes[k][2]
                w = b[2] - b[0]
                edits.append({"el": boxes[k][1], "m": boxes[k][3], "content": boxes[k][0],
                              "fs": boxes[k][4], "target_tl": (cur, yc - (b[3] - b[1]) / 2)})
                cur += w + gap
        else:
            # 纵向堆叠：把每对里下面的往下推
            for i, j in pairs:
                if i not in comp or j not in comp:
                    continue
                b1, b2 = boxes[i][2], boxes[j][2]
                need = (b2[1] - b1[3]) + 0.8
                edits.append({"el": boxes[j][1], "m": boxes[j][3], "content": boxes[j][0],
                              "fs": boxes[j][4],
                              "target_tl": (b2[0], b2[1] + max(need, 0.8))})
    if not edits:
        return 0
    # 应用编辑：按内容+坐标匹配 <text>（多编辑逐个应用）
    for e in edits:
        raw = p.read_text(encoding="utf-8")
        el = e["el"]
        l0 = text_local_bbox(el, e["content"], e["fs"])
        if not l0:
            continue
        inv = mat_inv(e["m"])
        if inv is None:
            continue
        lx = inv[0] * e["target_tl"][0] + inv[2] * e["target_tl"][1] + inv[4]
        ly = inv[1] * e["target_tl"][0] + inv[3] * e["target_tl"][1] + inv[5]
        dx, dy = lx - l0[0], ly - l0[1]
        try:
            old_x, old_y = float(el.get("x", "0")), float(el.get("y", "0"))
        except ValueError:
            continue
        new_x, new_y = old_x + dx, old_y + dy
        pat = re.compile(r'<text\b[^>]*>.*?</text>|<text\b[^>]*/>', re.S)
        done = [False]

        def sub(mm):
            if done[0]:
                return mm.group(0)
            tag = mm.group(0)
            try:
                mx = float(dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]).__iter__()).get("x", "nan"))
            except Exception:  # noqa: BLE001
                return tag
            d = dict(leg.ATTR_RE.findall(tag[: tag.index(">") + 1]))
            if d.get("x") is None or d.get("y") is None:
                return tag
            try:
                if (abs(float(d["x"]) - old_x) < 1e-6 and abs(float(d["y"]) - old_y) < 1e-6
                        and re.sub(r"<[^>]+>", "", tag).strip() == e["content"]):
                    done[0] = True
                    tag = re.sub(r'([\s])x="[^"]*"', rf'\g<1>x="{round(new_x, 2)}"', tag, count=1)
                    return re.sub(r'([\s])y="[^"]*"', rf'\g<1>y="{round(new_y, 2)}"', tag, count=1)
            except ValueError:
                return tag
            return tag

        raw = pat.sub(sub, raw)
        p.write_text(raw, encoding="utf-8")
    return n_pairs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    total_moved = total_stuck = 0
    stuck_files = []
    residual = 0
    for p in sorted((ROOT / "assets").rglob("*.svg")):
        rel = str(p.relative_to(ROOT))
        if args.filter and args.filter not in rel:
            continue
        moved, stuck = process_file(p, fix=not args.dry)
        total_moved += len(moved)
        total_stuck += len(stuck)
        if stuck:
            stuck_files.append((rel, stuck))
        if not args.dry:
            r = overlap_fix_pass(p)
            if r > 0:
                redistribute_pass(p)
                r2 = overlap_fix_pass(p)
                if r2 > 0:
                    residual += r2
                    print(f"  RESIDUAL {rel}: {r2} 对重叠待人工")
    print(f"重排 {total_moved} 处；字号无法放置 {total_stuck} 处；重叠残留 {residual} 对")
    for rel, st in stuck_files[:60]:
        print("  STUCK", rel, st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
