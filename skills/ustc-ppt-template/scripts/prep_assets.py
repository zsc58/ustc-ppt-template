#!/usr/bin/env python3
"""USTC 模版素材加工：logo 重着色、照片裁剪、媒体替换图合成。

替换策略：每张替换图与原 USTB 媒体同尺寸（透明画布），新内容等比缩放后
居中放进原内容的 alpha 包围盒 → 幻灯片 XML 零改动也不破坏布局比例。
"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance

BASE = Path('.')
SRC_MEDIA = Path('/tmp/ustb_pptx_inspect/ppt/media')
OUT = BASE / 'ustc_assets'
REPL = OUT / 'media_replacements'
REPL.mkdir(parents=True, exist_ok=True)

USTC_BLUE = (37, 74, 165)        # #254AA5，取自 ustc_logo.pdf 实测
WHITE = (255, 255, 255)

# ---------- 工具 ----------

def pdf_to_png(pdf, out_prefix, dpi=600):
    subprocess.run(['pdftoppm', '-png', '-r', str(dpi), str(pdf), str(out_prefix)], check=True)
    return Path(f'{out_prefix}-1.png')

def ink_to_alpha(img, ink_gray):
    """白底实色线稿 → 透明底 alpha 蒙版（0-255）。ink_gray 为墨色灰度。"""
    g = img.convert('L')
    scale = 255.0 / max(1, 255 - ink_gray)
    return g.point(lambda v: max(0, min(255, round((255 - v) * scale))))

def colorize(alpha_mask, color, alpha_factor=1.0):
    """alpha 蒙版 + 目标色 → 透明底彩色图。"""
    img = Image.new('RGBA', alpha_mask.size, color + (0,))
    a = alpha_mask if alpha_factor == 1.0 else alpha_mask.point(lambda v: round(v * alpha_factor))
    img.putalpha(a)
    return img

def crop_to_alpha_bbox(img):
    bbox = img.getchannel('A').getbbox()
    return img.crop(bbox)

def content_bbox(path):
    """原媒体内容包围盒：RGBA 用 alpha，RGB 用非白色。"""
    im = Image.open(path)
    if 'A' in im.mode:
        return im.size, im.getchannel('A').getbbox()
    g = im.convert('L').point(lambda v: 255 if v < 245 else 0)
    return im.size, g.getbbox()

def fit_into(canvas_size, bbox, art):
    """art（RGBA，已裁紧）等比缩放居中放入 canvas 的 bbox。"""
    canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    s = min(bw / art.width, bh / art.height)
    art = art.resize((max(1, round(art.width * s)), max(1, round(art.height * s))), Image.LANCZOS)
    x = bbox[0] + (bw - art.width) // 2
    y = bbox[1] + (bh - art.height) // 2
    canvas.paste(art, (x, y), art)
    return canvas

def crop_16_9(img, v_anchor=0.5):
    """裁 16:9。v_anchor: 0=顶部, 0.5=居中, 1=底部（竖图选取哪段）。"""
    w, h = img.size
    th = round(w * 9 / 16)
    if th <= h:
        y0 = round((h - th) * v_anchor)
        return img.crop((0, y0, w, y0 + th))
    tw = round(h * 16 / 9)
    x0 = (w - tw) // 2
    return img.crop((x0, 0, x0 + tw, h))

def rounded(img, radius_ratio=0.06):
    """圆角裁剪。"""
    r = round(min(img.size) * radius_ratio)
    mask = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius=r, fill=255)
    out = img.convert('RGBA')
    out.putalpha(mask)
    return out

# ---------- 1. logo / 字样 / 校徽 ----------

print('== logos ==')
side_png = pdf_to_png(BASE / 'ustc_logo.pdf', '/tmp/ustc_emblem', dpi=600)
emblem_raw = Image.open(side_png)  # 圆形校徽，蓝墨
emblem_alpha = ink_to_alpha(emblem_raw, ink_gray=73)   # #254AA5 灰度≈73
emblem_blue = crop_to_alpha_bbox(colorize(emblem_alpha, USTC_BLUE))
emblem_white = crop_to_alpha_bbox(colorize(emblem_alpha, WHITE))
emblem_blue.save(OUT / 'emblem_blue.png')
emblem_white.save(OUT / 'emblem_white.png')

side2_png = pdf_to_png(Path('assets/ustc_logo_side.pdf'), '/tmp/ustc_side', dpi=600)
side_raw = Image.open(side2_png)   # 横版校徽，黑墨
side_alpha = ink_to_alpha(side_raw, ink_gray=0)
side_blue = crop_to_alpha_bbox(colorize(side_alpha, USTC_BLUE))
side_white = crop_to_alpha_bbox(colorize(side_alpha, WHITE))
side_blue.save(OUT / 'logo_side_blue.png')
side_white.save(OUT / 'logo_side_white.png')

wm_raw = Image.open(BASE / '中国科学技术大学logo（1）.png').convert('RGBA')
wm_alpha = wm_raw.getchannel('A')
wm_blue = crop_to_alpha_bbox(colorize(wm_alpha, USTC_BLUE))
wm_white = crop_to_alpha_bbox(colorize(wm_alpha, WHITE))
# 420px 偏小，放大 3 倍平滑一下备用
wm_blue = wm_blue.resize((wm_blue.width * 3, wm_blue.height * 3), Image.LANCZOS)
wm_white = wm_white.resize((wm_white.width * 3, wm_white.height * 3), Image.LANCZOS)
wm_blue.save(OUT / 'wordmark_blue.png')
wm_white.save(OUT / 'wordmark_white.png')

# ---------- 2. 照片 ----------

print('== photos ==')
P = {
    'cover':   ('19585951082bc229dc17b28da19ac9a9.jpg', 0.5),   # I❤科大 横
    'toc':     ('1dc1fa487d75f5db3b72fd3bd482aeb1.jpeg', 0.5),  # 湖景 横
    'section': ('6fd107bfd60f04815679ac49735bdd9c.jpg', 0.42),  # 樱花 竖：取中上花区
    'thanks':  ('a8bcd68b3f983e231f1ac4767a83793e.jpg', 0.45),  # 老建筑 竖：入口居中
}
bg = {}
for name, (f, anchor) in P.items():
    im = Image.open(BASE / f).convert('RGB')
    c = crop_16_9(im, anchor)
    if c.width < 1600:
        c = c.resize((1600, 900), Image.LANCZOS)
    elif c.width > 1920:
        c = c.resize((1920, 1080), Image.LANCZOS)
    # 轻微提对比、降一点亮度，让白色条带和文字更突出
    c = ImageEnhance.Contrast(c).enhance(1.05)
    c = ImageEnhance.Brightness(c).enhance(0.96)
    c.save(OUT / f'bg_{name}.jpg', quality=90)
    bg[name] = c
    print(' bg_%s %s' % (name, c.size))

# ---------- 3. 媒体替换图（同尺寸画布 + 原内容 bbox）----------

print('== media replacements ==')

def replace_with(src_name, art, out_name=None, transparent=False):
    size, bbox = content_bbox(SRC_MEDIA / src_name)
    if transparent:
        img = Image.new('RGBA', size, (0, 0, 0, 0))
    else:
        img = fit_into(size, bbox, art)
    img.save(REPL / (out_name or src_name))
    print(f' {src_name}: canvas={size} bbox={bbox} -> {"transparent" if transparent else "art"}')

# image3 横版 logo（照片浅底上使用，用科大蓝版）
replace_with('image3.png', side_blue)
# image1 主楼线稿(master3) -> 校徽水印；image2 校训牌匾(master3) -> 校名字样蓝
replace_with('image1.png', colorize(emblem_alpha, USTC_BLUE, 0.30).crop(colorize(emblem_alpha, USTC_BLUE).getchannel('A').getbbox()))
replace_with('image2.png', wm_blue)
# image7 封面底部图书馆线稿 / image20 体育馆线稿 / image6 银杏 -> 透明（净化，照片背景自带装饰性）
replace_with('image7.png', None, transparent=True)
replace_with('image20.png', None, transparent=True)
replace_with('image6.png', None, transparent=True)
# image8 目录页贝壳线稿 -> 校徽低透明度水印
replace_with('image8.png', colorize(emblem_alpha, USTC_BLUE, 0.16).crop(emblem_alpha.getbbox()))
# image9 转场页教学楼线稿 -> 湖景圆角照片卡
replace_with('image9.png', rounded(crop_16_9(Image.open(BASE / P['toc'][0]).convert('RGB'), 0.5)))
# image10 蓝渐变扇形 -> 色相迁移到科大蓝
fan = Image.open(SRC_MEDIA / 'image10.png').convert('RGBA')
import colorsys
px = fan.load()
for yy in range(fan.height):
    for xx in range(fan.width):
        r, g, b, a = px[xx, yy]
        if a == 0:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h = 222 / 360  # USTC 蓝色相
        r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
        px[xx, yy] = (round(r2 * 255), round(g2 * 255), round(b2 * 255), a)
fan.save(REPL / 'image10.png')
print(' image10.png: hue -> 222°')
# image11 篆书"稽實鼎新" -> 校名字样（蓝）
replace_with('image11.png', wm_blue)
# image12 USTB 完整校徽(竖排) -> USTC 圆徽 + 字样 竖排组合
gap = round(emblem_blue.width * 0.06)
comp_w = emblem_blue.width
wm_scaled = wm_blue.resize((comp_w, round(wm_blue.height * comp_w / wm_blue.width)), Image.LANCZOS)
comp = Image.new('RGBA', (comp_w, emblem_blue.height + gap + wm_scaled.height), (0, 0, 0, 0))
comp.paste(emblem_blue, (0, 0), emblem_blue)
comp.paste(wm_scaled, (0, emblem_blue.height + gap), wm_scaled)
replace_with('image12.png', comp)
# image4.jpeg (master2 USTB主楼照片) -> I❤科大照片，保持原图长宽比裁剪
im4 = Image.open(SRC_MEDIA / 'image4.jpeg')
target_ratio = im4.width / im4.height
src = Image.open(BASE / P['cover'][0]).convert('RGB')
w, h = src.size
if w / h > target_ratio:
    tw = round(h * target_ratio); x0 = (w - tw) // 2; cropped = src.crop((x0, 0, x0 + tw, h))
else:
    th = round(w / target_ratio); y0 = (h - th) // 2; cropped = src.crop((0, y0, w, y0 + th))
cropped = cropped.resize(im4.size, Image.LANCZOS) if cropped.width > im4.width else cropped
cropped.save(REPL / 'image4.jpeg', quality=90)
print(f' image4.jpeg: {cropped.size}')
# image5.jpeg 默认背景（封面照），各 slide 再单独轮换
bg['cover'].save(REPL / 'image5.jpeg', quality=90)
print(' image5.jpeg: cover photo')

print('DONE')
