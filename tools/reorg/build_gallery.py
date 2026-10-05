# -*- coding: utf-8 -*-
"""P5：构建根 index.html 唯一画廊。

数据源：assets 下各级 manifest（嵌入为 JS 常量，离线单文件可用）。
功能：搜索（zh/en/tags）+ 大类过滤 + series/format 过滤 + 中英切换（img 自动切 .en.svg，
UI 文案 data-i18n 同步）+ 亮暗主题（跟随系统 + data-theme 手动覆盖，四态组合可用）+
点击放大 + 分页。CSS 由 tools/gallery_theme.css() 注入（i18n × theme 四态骨架）。

用法：python3 tools/reorg/build_gallery.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from gallery_theme import css  # noqa: E402

ASSETS = ROOT / "assets"

CATS = [
    ("01", "cells-microbes", "细胞与微生物", "Cells & Microbes"),
    ("02", "genetics-omics", "遗传与组学", "Genetics & Omics"),
    ("03", "metabolism-phenotype", "代谢与表型", "Metabolism & Phenotype"),
    ("04", "phylogeny-evolution", "系统发育与进化", "Phylogeny & Evolution"),
    ("05", "ecology-biotech", "生态与应用", "Ecology & Biotech"),
    ("06", "lab-methods", "实验方法", "Lab Methods"),
    ("07", "glassware-consumables", "器皿与耗材", "Glassware & Consumables"),
    ("08", "instruments-apparatus", "仪器与装置", "Instruments"),
    ("09", "safety-signage", "安全与标识", "Safety & Signage"),
    ("10", "figure-elements", "图版构件", "Figure Elements"),
    ("11", "diagrams-charts", "图表与流程", "Diagrams & Charts"),
    ("12", "icons-ui", "图标与 UI", "Icons & UI"),
]
SERIES_ZH = {"classic": "经典插画", "atlas": "图谱", "icon24": "24×24 图标",
             "primitives": "通用图元", "labflow": "实验室流程"}
SERIES_EN = {"classic": "Classic", "atlas": "Atlas", "icon24": "24×24 Icon",
             "primitives": "Primitives", "labflow": "LabFlow"}
PAGE = 120


def collect():
    items = []
    for catno, dirname, czh, cen in CATS:
        cm = json.loads((ASSETS / f"{catno}-{dirname}" / "manifest.json").read_text(encoding="utf-8"))
        for s in cm["subdirs"]:
            sm = json.loads((ASSETS / f"{catno}-{dirname}" / s["id"] / "manifest.json").read_text(encoding="utf-8"))
            for it in sm["items"]:
                en = it["file"].replace(".svg", ".en.svg") if it.get("en") else ""
                items.append({
                    "f": f"assets/{catno}-{dirname}/{s['id']}/{it['file']}",
                    "en": (f"assets/{catno}-{dirname}/{s['id']}/{en}" if en else ""),
                    "z": it["name_zh"], "e": it["name_en"],
                    "t": ",".join(it["tags"]),
                    "s": it["series"], "fm": it["format"],
                    "c": it["category"], "sd": s["id"],
                    "sdz": s["name_zh"], "sde": s["name_en"],
                })
    return items


I18N = {
    "title": {"zh": "SciGlyph · 绘图素材库", "en": "SciGlyph — Scientific Illustration Assets"},
    "ai_note": {"zh": "⚠ 素材由 AI 辅助生成并经人工审查，使用前请自行核实科学准确性",
                "en": "⚠ AI-generated assets, human-reviewed — verify scientific accuracy before use"},
    "search_ph": {"zh": "搜索：名称 / 英文 / 标签…", "en": "Search: name / English / tags…"},
    "all_cats": {"zh": "全部大类", "en": "All categories"},
    "all_series": {"zh": "全部系列", "en": "All series"},
    "all_fmt": {"zh": "全部形态", "en": "All formats"},
    "lang": {"zh": "EN", "en": "中文"},
    "theme_auto": {"zh": "主题：跟随系统", "en": "Theme: system"},
    "theme_light": {"zh": "主题：亮色", "en": "Theme: light"},
    "theme_dark": {"zh": "主题：暗色", "en": "Theme: dark"},
    "empty": {"zh": "没有匹配的素材", "en": "No matching assets"},
    "prev": {"zh": "上一页", "en": "Prev"},
    "next": {"zh": "下一页", "en": "Next"},
    "fmt_illustration": {"zh": "插画", "en": "Illustration"},
    "fmt_diagram": {"zh": "示意图表", "en": "Diagram"},
    "fmt_icon": {"zh": "图标", "en": "Icon"},
    "close": {"zh": "关闭（Esc）", "en": "Close (Esc)"},
}


def main():
    items = collect()
    assert len(items) == 2830, len(items)
    data = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    i18n = json.dumps(I18N, ensure_ascii=False)
    cats_js = json.dumps([{"id": f"{n}-{d}", "zh": z, "en": e} for n, d, z, e in CATS],
                         ensure_ascii=False)
    series_js = json.dumps({"zh": SERIES_ZH, "en": SERIES_EN}, ensure_ascii=False)

    html = """<!doctype html>
<html lang="zh" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SciGlyph · 绘图素材库 · Scientific Illustration Assets</title>
<style>__CSS__</style>
</head>
<body>
<header>
  <h1><span data-i18n="title">SciGlyph · 绘图素材库</span><span class="ver">v1.0.0 · CC BY 4.0 · ZengZichao</span></h1>
  <p class="ainote" data-i18n="ai_note">⚠ 素材由 AI 辅助生成并经人工审查，使用前请自行核实科学准确性</p>
  <div class="controls">
    <input id="q" type="search" data-i18n-ph="search_ph" aria-label="search">
    <select id="cat" aria-label="category"></select>
    <select id="ser" aria-label="series"></select>
    <select id="fmt" aria-label="format"></select>
    <button id="lang" type="button"></button>
    <button id="theme" type="button" class="theme-toggle"></button>
    <span class="count" id="count" role="status"></span>
  </div>
</header>
<main>
  <div class="grid" id="grid"></div>
  <p class="empty" id="empty" data-i18n="empty" hidden>没有匹配的素材</p>
  <nav class="pager" id="pager" aria-label="pagination"></nav>
</main>
<div class="modal" id="modal" role="dialog" aria-modal="true" aria-label="preview">
  <button class="close" id="mclose" type="button" aria-label="close">✕</button>
  <div>
    <div class="stage"><img id="mimg" alt=""></div>
    <p class="cap" id="mcap"></p>
  </div>
</div>
<script>
const DATA=__DATA__, I18N=__I18N__, CATS=__CATS__, SERIES=__SERIES__, PAGE=__PAGE__;
const store = (() => { try { return window.localStorage; } catch (e) { const m = {}; return { getItem: k => m[k] ?? null, setItem: (k, v) => { m[k] = String(v); } }; } })();
let lang = store.getItem('gal-lang') || 'zh';
let theme = store.getItem('gal-theme') || 'auto';
let page = 1;
const $ = id => document.getElementById(id);
const t = k => I18N[k] && I18N[k][lang];
function applyI18n(){
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach(el => { const v = t(el.dataset.i18n); if (v) el.textContent = v; });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { const v = t(el.dataset.i18nPh); if (v) el.placeholder = v; });
  $('lang').textContent = t('lang');
  updateThemeBtn();
  const cats = [{id:'', zh:'__ALLCAT_ZH__', en:'__ALLCAT_EN__'}].concat(CATS);
  $('cat').innerHTML = cats.map(c => `<option value="${c.id}">${lang==='zh'?c.zh:c.en}</option>`).join('');
  $('cat').value = window._cat || '';
  const ser = [['','__ALLSER_ZH__','__ALLSER_EN__']].concat(Object.keys(SERIES.zh).map(k => [k, SERIES.zh[k], SERIES.en[k]]));
  $('ser').innerHTML = ser.map(([k,z,e]) => `<option value="${k}">${lang==='zh'?z:e}</option>`).join('');
  $('ser').value = window._ser || '';
  const fmts = [['','__ALLFMT_ZH__','__ALLFMT_EN__'],['illustration',t('fmt_illustration'),'Illustration'],['diagram',t('fmt_diagram'),'Diagram'],['icon',t('fmt_icon'),'Icon']];
  $('fmt').innerHTML = fmts.map(([k,z,e]) => `<option value="${k}">${lang==='zh'?z:e}</option>`).join('');
  $('fmt').value = window._fmt || '';
  document.title = lang==='zh' ? 'SciGlyph · 绘图素材库 · Scientific Illustration Assets' : 'SciGlyph — Scientific Illustration Assets · 绘图素材库';
}
function filtered(){
  const q = $('q').value.trim().toLowerCase();
  const cat = $('cat').value, ser = $('ser').value, fmt = $('fmt').value;
  return DATA.filter(it =>
    (!cat || it.c === cat) && (!ser || it.s === ser) && (!fmt || it.fm === fmt) &&
    (!q || it.z.toLowerCase().includes(q) || it.e.toLowerCase().includes(q) || it.t.toLowerCase().includes(q)));
}
function srcOf(it){
  if (!lang.startsWith('en') || !it.en) return it.f;
  return it.en;
}
function render(){
  const items = filtered();
  const pages = Math.max(1, Math.ceil(items.length / PAGE));
  if (page > pages) page = pages;
  const slice = items.slice((page-1)*PAGE, page*PAGE);
  $('empty').hidden = items.length > 0;
  $('grid').innerHTML = slice.map(it => {
    const name = lang==='zh' ? it.z : it.e;
    const alt = `${name} (${it.s} · ${it.fm})`;
    const sd = lang==='zh' ? it.sdz : it.sde;
    return `<figure class="card" tabindex="0" role="button" data-i="${DATA.indexOf(it)}" aria-label="${alt}">
      <div class="thumb"><img loading="lazy" src="${srcOf(it)}" alt="${alt}"></div>
      <figcaption class="name">${name}</figcaption>
      <div class="meta"><span class="badge">${it.s}</span><span class="sd">${sd}</span><span>${it.f.split('/')[1].slice(0,2)}</span></div>
    </figure>`;
  }).join('');
  $('count').textContent = `${items.length}`;
  const pg = $('pager');
  if (pages <= 1) { pg.innerHTML=''; }
  else {
    let btns = `<button ${page<=1?'disabled':''} data-pg="${page-1}" aria-label="${t('prev')}">‹</button>`;
    const lo = Math.max(1, page-4), hi = Math.min(pages, lo+8);
    for (let i=lo;i<=hi;i++) btns += `<button data-pg="${i}" aria-current="${i===page}">${i}</button>`;
    btns += `<button ${page>=pages?'disabled':''} data-pg="${page+1}" aria-label="${t('next')}">›</button>`;
    pg.innerHTML = btns;
  }
}
function updateThemeBtn(){
  const key = theme==='auto' ? 'theme_auto' : theme==='light' ? 'theme_light' : 'theme_dark';
  $('theme').textContent = t(key);
  document.documentElement.dataset.theme = theme;
}
function openModal(idx){
  const it = DATA[idx];
  const name = lang==='zh' ? it.z : it.e;
  $('mimg').src = srcOf(it);
  $('mimg').alt = name;
  $('mcap').textContent = `${name} — ${it.f}`;
  $('modal').classList.add('open');
  $('mclose').focus();
}
function closeModal(){ $('modal').classList.remove('open'); }
document.addEventListener('click', e => {
  const card = e.target.closest('.card');
  if (card) { openModal(+card.dataset.i); return; }
  const pg = e.target.closest('[data-pg]');
  if (pg && !pg.disabled) { page = +pg.dataset.pg; render(); window.scrollTo(0,0); return; }
  if (e.target.id === 'modal' || e.target.id === 'mclose') closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
  if (e.key === 'Enter' && document.activeElement?.classList?.contains('card')) openModal(+document.activeElement.dataset.i);
});
['q','cat','ser','fmt'].forEach(id => {
  $(id).addEventListener('input', () => { window['_' + (id==='q'?'q':id)] = $(id).value; page = 1; render(); });
  $(id).addEventListener('change', () => {
    if (id!=='q') { window['_'+id] = $(id).value; page = 1; applyI18n(); render(); }
  });
});
$('lang').addEventListener('click', () => { lang = lang==='zh' ? 'en' : 'zh'; store.setItem('gal-lang', lang); applyI18n(); render(); });
$('theme').addEventListener('click', () => {
  theme = theme==='auto' ? 'light' : theme==='light' ? 'dark' : 'auto';
  store.setItem('gal-theme', theme); updateThemeBtn();
});
applyI18n();
render();
</script>
</body>
</html>
"""
    # 常量替换（避免与 CSS 花括号冲突，用标记替换）
    for k, v in {
        "__CSS__": css(), "__DATA__": data, "__I18N__": i18n,
        "__CATS__": cats_js, "__SERIES__": series_js, "__PAGE__": str(PAGE),
        "__ALLCAT_ZH__": "全部大类", "__ALLCAT_EN__": "All categories",
        "__ALLSER_ZH__": "全部系列", "__ALLSER_EN__": "All series",
        "__ALLFMT_ZH__": "全部形态", "__ALLFMT_EN__": "All formats",
    }.items():
        html = html.replace(k, v)
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html 生成：{len(items)} 素材，{len(html)//1024} KB")


if __name__ == "__main__":
    main()
