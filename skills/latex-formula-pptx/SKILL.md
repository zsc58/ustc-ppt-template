---
name: latex-formula-pptx
description: 把 PPT 中未渲染的 LaTeX/数学公式渲染成透明底 PNG 并按原比例插入幻灯片。Use when a .pptx contains unrendered math/LaTeX (plain-text formulas like P_f^tar, $...$, U_IR >= 2), or when the user asks to add/replace rendered formulas in slides.
---

# LaTeX 公式 → PPT 图片渲染

把 PPT 里所有"没有渲染的公式"（纯文本写的数学式）用 LaTeX 渲染成**透明底 PNG**，
放到对应位置。核心纪律：**只整体等比缩放，绝不改变图片长宽比**；可以调整大小使其适配空间。

## 管线总览

1. **检测**：`python -m markitdown deck.pptx` 提取文本，找出形如 `P_f^tar`、`$...$`、
   `U_IR >= 2`、`10^-4` 等未渲染数学式；同时看渲染截图确认哪些公式已是图片。
2. **渲染**：`scripts/render_formula.py` —— pdflatex(standalone+amsmath) → pdftoppm 600dpi
   → Pillow 灰度作 alpha → 紧裁透明 PNG。
3. **插入**：`scripts/insert_formula.py`（python-pptx）—— 按图片像素比计算尺寸，等比放入目标框。

## 渲染

```bash
python3 scripts/render_formula.py 'P_f = \int_\Omega \mathbb{I}[g(x)\le 0]\,f_X(x)\,dx' \
    out.png --color FFFFFF --dpi 600 --display
```

- `--display`：分式/积分等大型结构用 display 样式；行内小式不加。
- **颜色规则**：浅底页用深色（`1F2937` 或 `000000`）；深色/照片底用白 `FFFFFF`；
  需要主题强调色时直接传主题色十六进制。同一公式可渲染多个颜色版本。
- 依赖：`pdflatex`（用户是 **TinyTeX**，装在 `~/Library/TinyTeX`，缺宏包直接
  `tlmgr install <pkg>`，**无需 sudo**；常缺 `standalone`、`preview`）、`pdftoppm`(poppler)、Pillow。

## 插入（等比，绝不拉伸）

```bash
# 在第 3 页 (2.0in, 1.5in) 处插入，等比缩放到宽 ≤3.5in、高 ≤1.0in
python3 scripts/insert_formula.py deck.pptx 3 formula.png --box 2.0 1.5 3.5 1.0
```

尺寸经验：行内小式高度 ≈ 正文字号（12pt 文字 ≈ 0.20–0.25in cap height，含上下标可到 0.35in）；
display 公式高度 0.6–0.9in。先按目标框算 `min(w_box/w_img, h_box/h_img)` 的缩放系数，宽高同乘。

## 替换 PPT 里已有的公式图片（不动 XML）

若公式已以图片形式存在、只需换内容：**新图合成在与原图相同像素尺寸的透明画布上，
内容等比放入原图 alpha 包围盒**，然后同名覆盖 `ppt/media/imageN.png`。
幻灯片 XML 完全不用改，版式比例不破坏：

```python
orig = Image.open('ppt/media/imageN.png'); size, bbox = orig.size, orig.getchannel('A').getbbox()
canvas = Image.new('RGBA', size, (0,0,0,0))
s = min((bbox[2]-bbox[0])/art.width, (bbox[3]-bbox[1])/art.height)
art = art.resize((round(art.width*s), round(art.height*s)), Image.LANCZOS)
canvas.paste(art, (bbox[0]+(bbox[2]-bbox[0]-art.width)//2, bbox[1]+(bbox[3]-bbox[1]-art.height)//2), art)
```

注意原 pic 元素可能带 `<a:alphaModFix>`（半透明）、`<a:biLevel>`（黑白阈值）、`<a:duotone>`
等效果，照片/彩色公式要在 XML 里删掉这些效果节点。

## 手动备选（无本地 LaTeX 时）

用在线编辑器 https://www.latexlive.com/home ：粘贴 LaTeX → 预览 → 导出 PNG（选透明背景、
最高分辨率）→ 按上面"插入"规则放入 PPT。同样不要改变图片比例。

## QA

改完用 LibreOffice 渲染逐页目检：

```bash
soffice --headless --convert-to pdf deck.pptx && pdftoppm -jpeg -r 100 deck.pdf slide
```

⚠️ WPS 制作的 pptx 若内嵌字体（`ppt/fonts/*.fntdata`），LibreOffice 会崩溃
（`lzcomp.c` assertion）。QA 时复制一份，删除 `ppt/fonts/`、`presentation.xml` 的
`<p:embeddedFontLst>`、rels 中 font 关系、`[Content_Types].xml` 的 `fntdata` 默认项后再转换；
正式交付文件保留内嵌字体。

检查点：公式与底色对比度、是否被拉伸变形、基线是否与同行文字对齐、是否遮挡其他元素。
