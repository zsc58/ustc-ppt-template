#!/usr/bin/env python3
"""在解包目录中新增 6 个 USTC 风格布局示例页（slide6-11，显示顺序插在致谢页前）。

页面家具（背景水印照片、导航条、底部波浪、标题、页码）从 slide4 提取复用；
内容元素（卡片、强调条、文本框、图片、表格）用模板生成。
"""
import re, shutil
from pathlib import Path

UN = Path('/tmp/ustc_work/unpacked')
ASSETS = Path('./work')
E = 914400  # EMU per inch
BLUE, DARK, GRAY, LIGHT = '254AA5', '1F2937', '6B7280', 'ECF0FA'

def emu(v): return str(round(v * E))

# ---------- 从 slide4 提取家具 ----------
s4 = (UN / 'ppt/slides/slide4.xml').read_text(encoding='utf-8')

def extract(xml, name, tag):
    """按 name 提取平衡的 <p:tag>...</p:tag> 片段。"""
    i = xml.find(f'name="{name}"')
    assert i >= 0, name
    start = xml.rfind(f'<p:{tag}>', 0, i)
    depth, j = 0, start
    pat = re.compile(r'<(/?)p:%s>' % tag)
    for m in pat.finditer(xml, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return xml[start:m.end()]
    raise RuntimeError(name)

def strip_tags(seg):
    return re.sub(r'<p:custDataLst>.*?</p:custDataLst>', '', seg, flags=re.S)

BG    = strip_tags(extract(s4, 'Picture 2', 'pic'))
NAV   = strip_tags(extract(s4, '组合 5', 'grpSp'))
WAVE  = strip_tags(extract(s4, '组合 4', 'grpSp'))
TITLE = strip_tags(extract(s4, 'TextBox 39', 'sp'))
PGNUM = strip_tags(extract(s4, 'TextBox 59', 'sp'))
CARD  = strip_tags(extract(s4, 'Rounded Rectangle 40', 'sp'))
ACCENT= strip_tags(extract(s4, 'Rectangle 41', 'sp'))
STRIP = strip_tags(extract(s4, 'Rectangle 46', 'sp'))

def set_xfrm(seg, x, y, w, h):
    seg = re.sub(r'<a:off x="-?\d+" y="-?\d+"/>', f'<a:off x="{emu(x)}" y="{emu(y)}"/>', seg, count=1)
    seg = re.sub(r'<a:ext cx="\d+" cy="\d+"/>', f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/>', seg, count=1)
    return seg

def set_idname(seg, sid, name):
    return re.sub(r'<p:cNvPr id="\d+" name="[^"]*"', f'<p:cNvPr id="{sid}" name="{name}"', seg, count=1)

def set_title_text(seg, text):
    runs = list(re.finditer(r'<a:r>.*?</a:r>', seg, re.S))
    rpr = re.search(r'<a:rPr[^>]*/>|<a:rPr[^>]*>.*?</a:rPr>', runs[0].group(0), re.S).group(0)
    new = f'<a:r>{rpr}<a:t>{text}</a:t></a:r>'
    return seg[:runs[0].start()] + new + seg[runs[-1].end():]

def card(sid, x, y, w, h):
    return set_xfrm(set_idname(CARD, sid, f'卡片{sid}'), x, y, w, h)

def accent(sid, x, y, h):
    return set_xfrm(set_idname(ACCENT, sid, f'强调条{sid}'), x, y, 0.05, h)

def strip_rect(sid, x, y, w, h):
    return set_xfrm(set_idname(STRIP, sid, f'深蓝条{sid}'), x, y, w, h)

def runs_xml(runs):
    out = []
    for t, sz, bold, color in runs:
        out.append(
            f'<a:r><a:rPr lang="zh-CN" altLang="en-US" sz="{sz}" b="{1 if bold else 0}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="微软雅黑"/><a:ea typeface="微软雅黑"/><a:cs typeface="微软雅黑"/></a:rPr>'
            f'<a:t>{t}</a:t></a:r>')
    return ''.join(out)

def textbox(sid, name, x, y, w, h, paras, anchor='t'):
    """paras: list of (runs, align, space_before_pt)；runs: list of (text, sz, bold, color)"""
    ps = []
    for runs, algn, spc in paras:
        ppr = f'<a:pPr algn="{algn}"'
        if spc:
            ppr += f'><a:spcBef><a:spcPts val="{spc * 100}"/></a:spcBef></a:pPr>'
        else:
            ppr += '/>'
        ps.append(f'<a:p>{ppr}{runs_xml(runs)}</a:p>')
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{anchor}">'
        f'<a:normAutofit/></a:bodyPr><a:lstStyle/>{"".join(ps)}</p:txBody></p:sp>')

def pic(sid, name, rid, x, y, w, h):
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="{name}"/>'
        f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')

def shape(sid, name, geom, x, y, w, h, fill, text=None, sz=1800, tcolor='FFFFFF'):
    tx = ''
    if text is not None:
        tx = (f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/>'
              f'<a:lstStyle/><a:p><a:pPr algn="ctr"/>{runs_xml([(text, sz, True, tcolor)])}</a:p></p:txBody>')
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
        f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr>{tx}</p:sp>')

def table_frame(sid, x, y, w, h, headers, rows, col_w):
    cw = [emu(c) for c in col_w]
    def cell(t, hdr, band):
        fill = BLUE if hdr else ('FFFFFF' if not band else LIGHT)
        color = 'FFFFFF' if hdr else DARK
        ln = ('<a:lnL w="6350"><a:solidFill><a:srgbClr val="BCC9E8"/></a:solidFill></a:lnL>'
              '<a:lnR w="6350"><a:solidFill><a:srgbClr val="BCC9E8"/></a:solidFill></a:lnR>'
              '<a:lnT w="6350"><a:solidFill><a:srgbClr val="BCC9E8"/></a:solidFill></a:lnT>'
              '<a:lnB w="6350"><a:solidFill><a:srgbClr val="BCC9E8"/></a:solidFill></a:lnB>')
        return (f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="ctr"/>'
                f'{runs_xml([(t, 1300, hdr, color)])}</a:p></a:txBody>'
                f'<a:tcPr anchor="ctr" marL="91440" marR="91440">{ln}'
                f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')
    rh = emu(h / (len(rows) + 1))
    trs = ['<a:tr h="%s">%s</a:tr>' % (rh, ''.join(cell(t, True, False) for t in headers))]
    for i, r in enumerate(rows):
        trs.append('<a:tr h="%s">%s</a:tr>' % (rh, ''.join(cell(t, False, i % 2 == 1) for t in r)))
    return (
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="表格{sid}"/>'
        f'<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
        f'<p:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></p:xfrm>'
        f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f'<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>'
        + ''.join(f'<a:gridCol w="{c}"/>' for c in cw) +
        f'</a:tblGrid>{"".join(trs)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')

# ---------- 组装一页 ----------
HEAD = ('<?xml version="1.0" encoding="utf-8"?>\n'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
TAIL = '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'

def page(title, pageno, content):
    t = set_title_text(TITLE, title)
    pg = re.sub(r'<a:t>\d+ / \d+</a:t>', f'<a:t>{pageno} / 11</a:t>', PGNUM)
    return HEAD + BG + NAV + WAVE + t + pg + ''.join(content) + TAIL

RELS_BASE = '''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId20" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId21" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image5.jpeg"/>
  <Relationship Id="rId22" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image12.png"/>
%s</Relationships>
'''
IMG_REL = '  <Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/%s"/>\n'

# ---------- 新媒体 ----------
MEDIA = {
    'image33.png': ASSETS / 'card_sakura_43.png',
    'image34.png': ASSETS / 'formulas/f_gauss_dark.png',
    'image35.png': ASSETS / 'formulas/f_pf_white.png',
    'image36.png': ASSETS / 'formulas/f_inline_blue.png',
}
for dst, src in MEDIA.items():
    shutil.copy(src, UN / 'ppt/media' / dst)

bullets = lambda *ts: [([(t, 1200, False, DARK)], 'l', 6) for t in ts]
sub = lambda t: ([(t, 1500, True, BLUE)], 'l', 0)

slides = {}

# S6 两栏图文
slides['slide6'] = (page('【两栏图文页 — 左侧要点 · 右侧配图】', 5, [
    card(9001, 0.45, 1.55, 6.20, 4.45),
    accent(9002, 0.45, 1.67, 4.21),
    textbox(9003, '左栏文本', 0.63, 1.75, 5.85, 4.10,
            [sub('要点小标题（示例）')] + bullets(
                '• 第一条要点：替换为你的内容，建议每条一行到两行',
                '• 第二条要点：左侧文字与右侧配图相互呼应',
                '• 第三条要点：保持每条要点句式一致、长度接近',
                '• 第四条要点：素材照片可在 ustc_assets 中更换')),
    pic(9004, '右侧配图', 'rId30', 7.00, 1.62, 5.88, 4.41),
    textbox(9005, '图注', 7.00, 6.10, 5.88, 0.35,
            [([('图注示例：中国科大校园（樱花季）', 1100, False, GRAY)], 'ctr', 0)]),
]), {'rId30': 'image33.png'})

# S7 三卡片
cards7 = []
for i, (t, b1, b2, b3) in enumerate([
    ('论点一（示例）', '• 支撑材料或数据', '• 简要说明一句话', '• 对应章节索引'),
    ('论点二（示例）', '• 支撑材料或数据', '• 简要说明一句话', '• 对应章节索引'),
    ('论点三（示例）', '• 支撑材料或数据', '• 简要说明一句话', '• 对应章节索引')]):
    x = 0.45 + i * 4.25
    cards7 += [card(9101 + i * 10, x, 1.62, 3.94, 3.30),
               accent(9102 + i * 10, x, 1.74, 3.06),
               textbox(9103 + i * 10, f'卡片文本{i}', x + 0.18, 1.85, 3.58, 2.95,
                       [sub(t)] + bullets(b1, b2, b3))]
slides['slide7'] = (page('【三要点卡片页 — 并列论点】', 6, cards7 + [
    strip_rect(9131, 0.45, 5.30, 12.43, 0.62),
    textbox(9132, '结论条文本', 0.75, 5.30, 11.83, 0.62,
            [([('结论条示例：三条论点共同支撑本页核心观点（替换为你的结论）', 1300, True, 'FFFFFF')], 'ctr', 0)], anchor='ctr'),
]), {})

# S8 数据展示
stats = [('87.5%', '指标一名称（示例）'), ('10⁴', '指标二名称（示例）'), ('×3.2', '指标三名称（示例）')]
content8 = []
for i, (num, label) in enumerate(stats):
    x = 0.45 + i * 4.25
    content8 += [card(9201 + i * 10, x, 1.62, 3.94, 1.65),
                 textbox(9202 + i * 10, f'大数字{i}', x, 1.78, 3.94, 1.35,
                         [([(num, 4000, True, BLUE)], 'ctr', 0),
                          ([(label, 1100, False, GRAY)], 'ctr', 4)])]
content8 += [card(9231, 0.45, 3.55, 12.43, 2.35),
             textbox(9232, '图表占位', 0.45, 3.55, 12.43, 2.35,
                     [([('（图表占位区 — 在此粘贴图表 / 截图 / 示意图）', 1400, False, GRAY)], 'ctr', 0)], anchor='ctr')]
slides['slide8'] = (page('【数据展示页 — 关键指标 + 图表区】', 7, content8), {})

# S9 流程时间线
content9 = [shape(9301, '时间线', 'rect', 0.95, 3.40, 11.43, 0.03, BLUE)]
steps = [('阶段一（示例）', '阶段说明文字，替换为你的内容'),
         ('阶段二（示例）', '阶段说明文字，替换为你的内容'),
         ('阶段三（示例）', '阶段说明文字，替换为你的内容'),
         ('阶段四（示例）', '阶段说明文字，替换为你的内容')]
for i, (t, d) in enumerate(steps):
    cx = 2.10 + i * 3.05
    content9 += [shape(9302 + i * 10, f'节点{i}', 'ellipse', cx - 0.275, 3.14, 0.55, 0.55, BLUE, str(i + 1), 1600),
                 textbox(9303 + i * 10, f'阶段标题{i}', cx - 1.30, 2.45, 2.60, 0.45,
                         [([(t, 1400, True, DARK)], 'ctr', 0)]),
                 textbox(9304 + i * 10, f'阶段说明{i}', cx - 1.30, 3.95, 2.60, 0.95,
                         [([(d, 1100, False, GRAY)], 'ctr', 0)])]
slides['slide9'] = (page('【流程页 — 横向时间线】', 8, content9), {})

# S10 公式演示
content10 = [
    card(9401, 0.45, 1.55, 6.20, 2.10),
    textbox(9402, '公式标签1', 0.63, 1.70, 5.85, 0.40, [sub('浅底深色公式（示例：高斯密度）')]),
    pic(9403, '公式1', 'rId31', 1.78, 2.30, 3.55, 0.80),       # 842x190 → 4.43:1
    card(9404, 6.95, 1.55, 5.93, 2.10),
    textbox(9405, '公式标签2', 7.13, 1.70, 5.58, 0.40, [sub('行内小公式（科大蓝，示例：判停准则）')]),
    pic(9406, '公式2', 'rId32', 9.05, 2.42, 1.72, 0.44),        # 277x71 → 3.90:1
    strip_rect(9407, 0.45, 4.00, 12.43, 1.30),
    pic(9408, '公式3', 'rId33', 0.95, 4.27, 4.37, 0.76),        # 1086x189 → 5.74:1
    textbox(9409, '公式说明', 5.75, 4.12, 6.90, 1.06,
            [([('深底白色公式（示例：失效概率积分）', 1400, True, 'FFFFFF')], 'l', 0),
             ([('渲染管线：LaTeX → pdflatex → 透明 PNG → 等比插入', 1100, False, 'BCC9E8')], 'l', 5)], anchor='ctr'),
    textbox(9410, '页脚注', 0.45, 5.55, 12.43, 0.40,
            [([('公式不要拉伸变形：只整体缩放，保持原始长宽比；浅底用深色、深底用白色。', 1100, False, GRAY)], 'l', 0)]),
]
slides['slide10'] = (page('【公式页 — LaTeX 公式渲染示例】', 9, content10),
                     {'rId31': 'image34.png', 'rId32': 'image36.png', 'rId33': 'image35.png'})

# S11 表格
slides['slide11'] = (page('【表格页 — 数据对比】', 10, [
    table_frame(9501, 1.20, 1.75, 10.93, 3.30,
                ['对比项', '方案 A（示例）', '方案 B（示例）', '备注'],
                [['计算成本', '10⁶ 次调用', '10⁴ 次调用', '低成本'],
                 ['适用场景', '通用', '小失效概率', '示例文字'],
                 ['精度', '基准', '相当', '示例文字'],
                 ['实现难度', '低', '中', '示例文字']],
                [2.20, 3.30, 3.30, 2.13]),
    textbox(9502, '表注', 1.20, 5.35, 10.93, 0.40,
            [([('表注示例：表头科大蓝、隔行浅蓝底，可直接增删行列。', 1100, False, GRAY)], 'l', 0)]),
]), {})

# ---------- 写文件 ----------
for name, (xml, extra_rels) in slides.items():
    (UN / f'ppt/slides/{name}.xml').write_text(xml, encoding='utf-8')
    rels = RELS_BASE % ''.join(IMG_REL % (rid, f) for rid, f in extra_rels.items())
    (UN / f'ppt/slides/_rels/{name}.xml.rels').write_text(rels, encoding='utf-8')
    print('wrote', name)

# ---------- 注册 ----------
# [Content_Types].xml（幂等）
ct = UN / '[Content_Types].xml'
xml = ct.read_text(encoding='utf-8')
adds = ''.join(f'<Override PartName="/ppt/slides/{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
               for n in slides if f'/ppt/slides/{n}.xml' not in xml)
xml = xml.replace('</Types>', adds + '</Types>')
ct.write_text(xml, encoding='utf-8')

# presentation.xml.rels（幂等）
pr = UN / 'ppt/_rels/presentation.xml.rels'
xml = pr.read_text(encoding='utf-8')
new_rids = {}
adds = ''
for n in slides:
    m = re.search(r'Id="(rId\d+)"[^>]*Target="slides/%s\.xml"' % n, xml)
    if m:
        new_rids[n] = m.group(1)
        continue
    maxr = max(int(x) for x in re.findall(r'Id="rId(\d+)"', xml + adds))
    rid = f'rId{maxr + 1}'
    new_rids[n] = rid
    adds += f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/{n}.xml"/>'
xml = xml.replace('</Relationships>', adds + '</Relationships>')
pr.write_text(xml, encoding='utf-8')

# presentation.xml: sldIdLst，插在 slide5 的 sldId 前（幂等）
pp = UN / 'ppt/presentation.xml'
xml = pp.read_text(encoding='utf-8')
prels = pr.read_text(encoding='utf-8')
s5rid = re.search(r'Id="(rId\d+)"[^>]*Target="slides/slide5\.xml"', prels).group(1)
maxsid = max(int(m) for m in re.findall(r'<p:sldId id="(\d+)"', xml))
missing = [n for n in slides if f'r:id="{new_rids[n]}"' not in xml]
entries = ''.join(f'<p:sldId id="{maxsid + i}" r:id="{new_rids[n]}"/>' for i, n in enumerate(missing, 1))
if entries:
    m = re.search(r'<p:sldId id="\d+" r:id="%s"/>' % s5rid, xml)
    assert m, 'slide5 sldId not found'
    xml = xml[:m.start()] + entries + xml[m.start():]
    pp.write_text(xml, encoding='utf-8')

# slide4 页码 4/27 -> 4/11
s4p = UN / 'ppt/slides/slide4.xml'
xml = s4p.read_text(encoding='utf-8')
xml = xml.replace('<a:t>4 / 27</a:t>', '<a:t>4 / 11</a:t>')
s4p.write_text(xml, encoding='utf-8')

print('registered:', new_rids)
