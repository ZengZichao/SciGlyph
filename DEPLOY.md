# 部署到 GitHub Pages

SciGlyph 的画廊是一个**零构建**的静态站点：`index.html` 内联了全部素材索引，
缩略图按相对路径 `assets/…` 直接引用 SVG，没有打包步骤、没有外部 CDN、没有后端。
因此 Pages 只需要把仓库里的文件原样发布出去。

## 一、本地验证（发布前先跑这一套）

```bash
python3 tools/check_repo.py        # 素材与元数据总闸门（含可渲染性）
python3 tools/check_site.py        # 画廊索引与 assets/ 一一对应、页面自包含
python3 tools/build_site.py        # 装配发布产物到 site/
python3 -m http.server -d site 8000  # 本地预览
```

浏览器打开 <http://localhost:8000/> 即可看到与线上一致的效果。
`site/` 是可重建产物，已在 `.gitignore` 中，不需要提交。

> 直接双击 `index.html` 也能用（画廊不依赖 fetch），但 Pages 上走的是 HTTP，
> 所以发布前请用上面的 http 预览确认一遍。

## 二、开启 Pages

1. 把仓库推到 GitHub（默认分支 `main`）。
2. 仓库 **Settings → Pages → Build and deployment** 里 Source 选 **GitHub Actions**。
3. 本仓库自带工作流 `.github/workflows/pages.yml`：
   它在 `push` 到 `main`（以及手动触发）时先跑上面两个质检闸门，
   再用 `build_site.py` 装配 `site/`，最后通过官方
   `actions/upload-pages-artifact` + `actions/deploy-pages` 发布。
   任何一项闸门失败，部署会中止，不会把坏素材发上去。
4. 首次运行后可在 **Actions** 页面看到 "Deploy gallery to Pages"，
   日志末尾给出的 `Page URL` 形如 `https://<用户名>.github.io/<仓库名>/`。

之后每次推送到 `main` 都会自动重新发布；也可以在 Actions 里手动
"Run workflow" 触发一次部署。

## 三、改了素材之后

| 改了什么 | 需要重跑 |
|---|---|
| `assets/**` 里的 SVG | `python3 tools/check_repo.py` |
| `manifest.json` 的名称 / 描述 / 标签 | `python3 tools/reorg/build_gallery.py` 重新生成 `index.html` |
| 新增或删除素材 | `build_gallery.py` + `check_site.py` |
| README / SPEC / NOTICE | `python3 tools/reorg/docs_gen.py` |

`index.html` 由 `tools/reorg/build_gallery.py` 生成，请勿手工编辑，
否则下一次生成会覆盖你的改动。

## 四、访问控制与限制

- GitHub Pages 的项目站点是公开可访问的（知道地址的人都能看到），
  免费版不支持给 Pages 加密码。
- 单个 Pages 站点软上限 1 GB、每月 100 GB 带宽；本仓库产物约 11 MB，
  3090 个 SVG 单文件平均 2.4 KB，远低于限制。
- 仓库根目录的 `.nojekyll` 让 Pages 跳过 Jekyll 处理，
  避免任何以下划线开头的路径被忽略；`build_site.py` 也会在 `site/` 里写一份。
