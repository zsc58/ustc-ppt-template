---
name: ustc-ppt-template
description: 中国科学技术大学（USTC）蓝色学术 PPT 模版与配套素材。Use when the user wants to make a USTC-styled presentation, fill the 科大/USTC template with content, create slides for a report/defense/组会, or needs USTC logos, campus photos, or the USTC blue palette.
---

# USTC 蓝色学术 PPT 模版

成品模版：`assets/模板_USTC蓝色学术_v1.pptx`（15 页，16:9，内嵌 WPS 字体，**含全套跳转超链接**）。
设计源自同学的 USTB 模版，配色/校徽/照片已全部 USTC 化。
页序：1 封面 / 2 目录 / 3 PART1 / 4 内容页 / 5–10 六种布局示例页 / 11–14 PART2–5 / 15 致谢。

⚠️ **slide 文件名 ≠ 显示页码**：WPS 保存会按显示顺序重命名 slideN.xml 和 media 文件，
任何脚本都必须按 `presentation.xml` 的 sldIdLst 解析显示顺序、按内容特征识别页面/媒体，
不能硬编码文件名。

## 用内容填充模版（标准流程）

1. **复制模版**到目标位置改名，绝不在 skill 内的原件上改。
2. **规划页型**：每段内容选对应示例页 —— 要点对比→三卡片页(p6)；图文混排→两栏页(p5)；
   指标数据→数据页(p7)；方法流程→时间线页(p8)；公式推导→公式页(p9)；参数/方案对比→表格页(p10)；
   密集内容参考 p4。需要 N 个同类页就把该页复制 N 份。
3. **复制页的做法**（python-pptx 不支持直接复制页）：解包后复制 `slideN.xml` + 其
   `_rels/slideN.xml.rels`，在 `[Content_Types].xml`、`ppt/_rels/presentation.xml.rels`、
   `presentation.xml` 的 `sldIdLst`（按显示顺序插入）登记；或用 `scripts/build_new_slides.py`
   里的现成注册逻辑（幂等）。
4. **填文字**：直接替换 XML 中的 `<a:t>` 文本。所有【】和"（示例）"字样都是占位符。
   注意 p4 的行内公式图片按原文字宽度对位，**改该页文字会导致公式错位**。
5. **每页手工项**：顶部"导航一~五"改成实际章节名（当前章节高亮的样式已做好）；
   页码文本（如 `5 / 11`）按最终页数统一改；封面/致谢页的标题、姓名、日期。
6. **公式**：一律用 `latex-formula-pptx` skill 渲染成透明 PNG 等比插入（浅底深字/深底白字）。
7. **QA**：LibreOffice 渲染逐页目检。⚠️ 本模版含 WPS 内嵌字体，LibreOffice 会崩溃
   （lzcomp 断言）——QA 前复制一份，删 `ppt/fonts/`、`presentation.xml` 的
   `<p:embeddedFontLst>` 与 `embedTrueTypeFonts`、rels 的 font 关系、Content_Types 的
   `fntdata` 项再转 PDF。**交付文件必须保留内嵌字体**（方正小标宋/微软雅黑/华文中宋/汉仪颜楷，本机未装）。

## 配色（科大蓝以 assets/ustc_logo.pdf 实测为准）

| 角色 | 色值 |
|---|---|
| 主色（科大蓝） | `254AA5` |
| 亮蓝强调 | `4D74C8` |
| 浅蓝底 | `ECF0FA` |
| 浅蓝辅助/分隔 | `BCC9E8` |
| 高亮点缀 | `92ADEC` |
| 正文深灰 | `1F2937` |

## assets/ 素材清单

- `模板_USTC蓝色学术_v1.pptx` — 成品模版
- `ustc_logo.pdf`（圆形校徽矢量，权威蓝色来源）、`ustc_logo_side.pdf`（横版校徽矢量，黑色）
- `emblem_blue/white.png`、`logo_side_blue/white.png` — 校徽位图（科大蓝/白，透明底）
- `wordmark_blue/white.png`（完整横版组合字样）、`wordmark_textonly_blue.png`（去小徽文字块）、
  `中国科学技术大学logo（1）.png`（原始白色字样，要校名字体时用图不用字体）
- `bg_cover/toc/section/thanks.jpg` — 四张校园照 16:9 裁剪版（I❤科大/湖景/樱花/老建筑）
- `card_sakura_43.png` — 樱花 4:3 圆角卡
- `photos_original/` — 四张校园照原图（需要重新裁剪时用）

## 超链接导航（已接好，章节数变化后一键重接）

模版内置 129 处跳转：目录五项 → 各 PART 转场页；每个内容页导航条（平行四边形+文本框）→
对应 PART 页；导航条页眉 logo 与转场页左上 logo → 跳回目录。全部加在**形状层 cNvPr**
（`<a:hlinkClick r:id=... action="ppaction://hlinksldjump"/>`），不影响文字样式。

两条 WPS 实测教训（脚本已内置应对）：
1. **WPS 按 slide 文件名序号当页码跳转**（不真正解析关系目标），PowerPoint 按关系解析。
   脚本接线前会先把 slideN.xml 重排成"文件名=显示页码"，两种解析就一致了，WPS/Office 行为相同。
   若之后在 PowerPoint 里调整过页面顺序（PPT 不改文件名），重跑一次脚本即可恢复一致。
2. **WPS 不支持组合（group）级超链接**，脚本会把目录组合内的每个形状单独接线。

填充实际内容、复制/增删章节页后，重跑一次即可全部重新接线（幂等）：

```bash
python3 scripts/wire_nav_links.py 你的文件.pptx            # 自动检测目录页/PART页/导航页
python3 scripts/wire_nav_links.py 你的文件.pptx --map 2=12  # 手动指定 章节2→第12页
```

自动检测规则：目录页含「目录」文本；章节 N 转场页恰好含一个「PART N」文本；内容页含「导航一」。
改了这些文案（如 PART→第X章）就用 `--map` 手动指定。注意：LibreOffice 导出 PDF 不保留这类
页内跳转注释，验证以 WPS/PowerPoint 实际点击或 python-pptx 读取 `click_action.target_slide` 为准。

## scripts/（构建脚本，留作参考与复用）

- `prep_assets.py` — 素材加工：PDF→PNG、亮度→alpha 重着色、16:9 裁剪、
  **同画布包围盒换图法**（替换 pptx 媒体不动 XML 的关键技巧）
- `transform_pptx.py` — 全局色替换、媒体替换、背景轮换的做法
- `build_new_slides.py` — 从现有页提取"家具"（导航/波浪/标题/页码）拼装新页 + 幂等注册新 slide
- 注意：脚本内是绝对路径且依赖已删除的 USTB 原始文件，**直接跑不通**，按需改路径取用其中函数/手法。

## 经验坑

- pic 元素可能带 `<a:alphaModFix>`（半透明）/`<a:biLevel>`（黑白阈值）效果，换照片要在 XML 删掉
- 页眉 logo 是用 `srcRect` 裁剪 `image12.png`（校徽+字样竖排组合）的两个区域实现的，
  改 image12 时保持"上徽下字"的竖排比例
- zsh 下 `rm slide-*.jpg` 通配失败会中止整条命令，脚本里用 `rm -f ... 2>/dev/null` 或加分号
