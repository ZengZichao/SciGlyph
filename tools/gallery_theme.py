#!/usr/bin/env python3
"""统一画廊 CSS（i18n × theme 四态骨架）。

对外接口（供根 index.html 构建器 tools/reorg/build_gallery.py 内嵌）：
  css()          —— 完整样式表：亮/暗变量（data-theme 手动覆盖 + prefers-color-scheme 跟随）
                    + 打印样式 + 布局/卡片/控件/对话框规则。
  LIGHT / DARK   —— 两态变量字典（:root[data-theme=…] 生成用）。

四态组合 = {zh,en} × {light,dark}：语言只影响 UI 文案（JS data-i18n），主题由 CSS 变量切换；
本文件保证两主题的对比度（正文 ≥ 7:1，次要文字 ≥ 4.5:1）。
"""
from __future__ import annotations

LIGHT = {
    "--bg": "#F6F7F9", "--surface": "#FFFFFF", "--ink": "#1B2733",
    "--ink-2": "#5A6B7B", "--line": "#D9DEE4", "--accent": "#1F6F8B",
    "--accent-ink": "#FFFFFF", "--chip": "#EDF1F5", "--thumb-bg": "#FFFFFF",
    "--shadow": "0 1px 3px rgba(27,39,51,.12)",
}
DARK = {
    "--bg": "#12161C", "--surface": "#1A2028", "--ink": "#E8EDF2",
    "--ink-2": "#9AAAB8", "--line": "#2C3642", "--accent": "#6CC3E8",
    "--accent-ink": "#0E1319", "--chip": "#232B35", "--thumb-bg": "#F2F4F6",
    "--shadow": "0 1px 3px rgba(0,0,0,.5)",
}


def _vars(d: dict, selector: str) -> str:
    body = ";".join(f"{k}:{v}" for k, v in d.items())
    return f"{selector}{{{body}}}"


def css() -> str:
    light = _vars(LIGHT, ":root,:root[data-theme=light]")
    dark_manual = _vars(DARK, ":root[data-theme=dark]")
    dark_auto = (_vars(DARK, ":root")
                 .replace(":root{", ":root{", 1))
    dark_block = f"@media (prefers-color-scheme:dark){{{dark_auto}}}"
    print_block = (
        "@media print{"
        "header,.controls,.pager,.modal,.theme-toggle,.lang-toggle{display:none!important}"
        "body{background:#fff;color:#000}"
        "main{max-width:none;padding:0}"
        ".grid{grid-template-columns:repeat(5,1fr);gap:6mm}"
        ".card{border:1px solid #bbb;break-inside:avoid;box-shadow:none!important;background:#fff}"
        ".thumb{background:#fff;border:none}"
        ".badge,.meta{color:#000}"
        "}"
    )
    layout = """
*{box-sizing:border-box}
html{font-size:15px}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',Inter,Helvetica,Arial,sans-serif;
  line-height:1.5;transition:background .2s,color .2s}
header{position:sticky;top:0;z-index:10;background:var(--surface);
  border-bottom:1px solid var(--line);padding:.7rem .9rem;box-shadow:var(--shadow)}
h1{font-size:1.05rem;margin:0 0 .5rem;display:flex;gap:.6rem;align-items:baseline;flex-wrap:wrap}
h1 .ver{font-size:.72rem;color:var(--ink-2);font-weight:400}
.ainote{font-size:.72rem;color:var(--ink-2);margin:0 0 .45rem}
.controls{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.controls input[type=search]{flex:1 1 14rem;min-width:10rem;padding:.42rem .7rem;
  border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:.9rem}
.controls select{padding:.4rem .5rem;border:1px solid var(--line);border-radius:8px;
  background:var(--bg);color:var(--ink);font-size:.85rem}
.controls button{padding:.4rem .75rem;border:1px solid var(--line);border-radius:8px;
  background:var(--chip);color:var(--ink);cursor:pointer;font-size:.85rem}
.controls button:hover{border-color:var(--accent)}
.count{font-size:.78rem;color:var(--ink-2);margin-left:auto}
main{max-width:none;margin:0;padding:.75rem .6rem 1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:.5rem}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:.5rem;margin:0;cursor:zoom-in;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:.35rem;min-width:0}
.card:hover{border-color:var(--accent)}
.thumb{background:var(--thumb-bg);border-radius:6px;aspect-ratio:4/3;width:100%;
  display:flex;align-items:center;justify-content:center;overflow:hidden}
.thumb img{max-width:92%;max-height:92%;display:block}
.name{font-size:.8rem;font-weight:600;line-height:1.3;margin:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{font-size:.68rem;color:var(--ink-2);display:flex;gap:.35rem;flex-wrap:wrap}
.meta .sd{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.badge{background:var(--chip);border-radius:4px;padding:0 .3rem;flex:none}
.empty{color:var(--ink-2);text-align:center;padding:3rem 0}
.pager{display:flex;gap:.4rem;justify-content:center;align-items:center;margin:1rem 0 1.5rem;flex-wrap:wrap}
.pager button{min-width:2.2rem;padding:.3rem .5rem;border:1px solid var(--line);
  border-radius:6px;background:var(--surface);color:var(--ink);cursor:pointer}
.pager button[aria-current=true]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.modal{position:fixed;inset:0;background:rgba(10,14,19,.72);display:none;
  align-items:center;justify-content:center;z-index:50;padding:2rem}
.modal.open{display:flex}
.modal .stage{background:var(--thumb-bg);border-radius:12px;max-width:min(86vw,880px);
  max-height:80vh;display:flex;align-items:center;justify-content:center;padding:1rem}
.modal .stage img{max-width:100%;max-height:74vh;width:auto;height:auto}
.modal .cap{color:#F2F4F6;text-align:center;margin-top:.7rem;font-size:.9rem;
  text-shadow:0 1px 2px rgba(0,0,0,.6);max-width:min(86vw,880px)}
.modal .close{position:absolute;top:1rem;right:1.2rem;background:none;border:none;
  color:#F2F4F6;font-size:1.6rem;cursor:pointer}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
:where(button,a,input,select,[tabindex]):focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:640px){.grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}}
"""
    return (f"{light}\n{dark_manual}\n{dark_block}\n{print_block}{layout}")
