// P5：index.html 四态（zh/en × light/dark）jsdom 交互测试。
// 运行：node tools/reorg/gallery.test.mjs
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

const html = readFileSync(path.join(ROOT, "index.html"), "utf-8");
let pass = 0, fail = 0;
function ok(cond, msg) {
  if (cond) { pass++; console.log("  PASS", msg); }
  else { fail++; console.log("  FAIL", msg); }
}

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  url: "http://localhost/index.html",
  pretendToBeVisual: true,
});
const { window } = dom;
const { document } = window;

function state() {
  return {
    cards: document.querySelectorAll("#grid .card").length,
    imgs: [...document.querySelectorAll("#grid .card img")],
    count: document.getElementById("count").textContent,
    lang: document.documentElement.lang,
    theme: document.documentElement.dataset.theme,
    title: document.title,
    i18nTitle: document.querySelector('[data-i18n="title"]').textContent,
  };
}

console.log("[1] 初始态（zh × auto→按 jsdom 默认 light）");
let s = state();
ok(s.cards === 120, `首屏渲染 120 卡片（实际 ${s.cards}）`);
ok(s.imgs.every(i => i.getAttribute("alt")), "全部 img 带 alt");
ok(s.count === "2830", `计数 2830（实际 ${s.count}）`);
ok(s.i18nTitle === "SciGlyph · 绘图素材库", "UI 文案为中文");
ok(s.imgs.some(i => i.getAttribute("src").endsWith(".svg")) &&
   s.imgs.every(i => !i.getAttribute("src").includes(".en.svg")), "中文模式 img 用原版 src");

console.log("[2] 切换到英文（img 换 .en.svg + UI 文案同步）");
document.getElementById("lang").click();
s = state();
ok(s.lang === "en", "html lang=en");
ok(s.i18nTitle === "SciGlyph — Scientific Illustration Assets", "UI 文案切英文");
ok(s.imgs.some(i => i.getAttribute("src").includes(".en.svg")), "含中文文本的素材 img 切 .en.svg");
ok(s.imgs.every(i => i.getAttribute("alt")), "英文模式 img 仍全带 alt");

console.log("[3] 主题手动覆盖三态");
const themeBtn = document.getElementById("theme");
themeBtn.click();
ok(state().theme === "light", "覆盖为 light");
themeBtn.click();
ok(state().theme === "dark", "覆盖为 dark");
ok(document.documentElement.getAttribute("data-theme") === "dark", "data-theme=dark 已写入（CSS 变量生效）");
themeBtn.click();
ok(state().theme === "auto", "回到跟随系统");
// 四态组合：en × dark
s = state();
ok(s.lang === "en" && s.theme === "auto" && s.cards === 120, "en × theme 组合仍正常渲染");

console.log("[4] 搜索 + 过滤");
const q = document.getElementById("q");
q.value = "coccus";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
s = state();
ok(+s.count > 0 && +s.count < 2830, `搜索 coccus 命中 ${s.count} 个`);
ok(s.cards <= 120, "结果分页上限 120");
document.getElementById("lang").click(); // 切回中文再搜
q.value = "球菌";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
ok(+document.getElementById("count").textContent > 0, "中文搜索 球菌 命中");
q.value = "";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
const cat = document.getElementById("cat");
cat.value = "09-safety-signage";
cat.dispatchEvent(new window.Event("change", { bubbles: true }));
const ser = document.getElementById("ser");
ser.value = "icon24";
ser.dispatchEvent(new window.Event("change", { bubbles: true }));
const cnt = +document.getElementById("count").textContent;
ok(cnt > 0, `大类+系列过滤命中 ${cnt} 个（09 × icon24）`);
const fmt = document.getElementById("fmt");
fmt.value = "icon";
fmt.dispatchEvent(new window.Event("change", { bubbles: true }));
ok(+document.getElementById("count").textContent === cnt, "形态过滤 icon 不缩小 09×icon24 集合");

console.log("[5] 点击放大（modal）");
const card = document.querySelector("#grid .card");
card.click();
ok(document.getElementById("modal").classList.contains("open"), "modal 打开");
ok(document.getElementById("mimg").getAttribute("src"), "modal img 有 src");
ok(document.getElementById("mcap").textContent.length > 0, "modal 有说明文字");
document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
ok(!document.getElementById("modal").classList.contains("open"), "Esc 关闭 modal");

console.log(`\n合计 ${pass} PASS / ${fail} FAIL`);
process.exit(fail ? 1 : 0);
