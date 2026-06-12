#!/usr/bin/env python3
"""USTC 模版超链接接线：目录项/导航条 → 章节转场页，页眉 logo → 目录页。

用法:
    python3 wire_nav_links.py 文件.pptx [--map 1=3 2=12 ...]
    python3 wire_nav_links.py 解包目录 [--map ...]

自动检测（可被 --map 章节号=显示页码 覆盖）：
- 目录页 = 含「目录」文本的页
- 章节 N 转场页 = 恰好含一个「PART N」文本的页（目录页含全部 PART 因而被排除）
- 内容页 = 含「导航一」文本的页

接线（全部加在形状层 cNvPr，不动文字样式）：
- 目录页顶层元素文本含「PART N」或「章节N」 → 跳转转场页 N
- 内容页导航条：「导航N」文本框 + 紧邻其前的平行四边形 → 转场页 N
- 导航条内页眉 logo 图片、转场页左上角 logo → 跳回目录页
- 找不到转场页 N 时跳过并告警；重复运行幂等（已有链接则更新目标）。

填充完实际内容、增删章节后重跑一次即可全部重新接线。
"""
import argparse, os, re, shutil, sys, tempfile, zipfile
from pathlib import Path

CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
SLIDE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide'


def slide_order(un: Path):
    """按显示顺序返回 slide 文件名列表。"""
    pres = (un / 'ppt/presentation.xml').read_text(encoding='utf-8')
    rels = (un / 'ppt/_rels/presentation.xml.rels').read_text(encoding='utf-8')
    rid2file = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="slides/([^"]+)"', rels))
    return [rid2file[r] for r in re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>', pres)]


def renumber_slides(un: Path):
    """把 slideN.xml 文件名重排成与显示顺序一致（N = 显示页码）。

    WPS 跳转按文件名序号当页码解析（不真正解析关系目标），文件名与顺序错位
    会导致跳错页；WPS 自己保存时会强制"文件名=页序"，这里提前对齐。
    """
    order = slide_order(un)
    mapping = {old: f'slide{i}.xml' for i, old in enumerate(order, 1) if old != f'slide{i}.xml'}
    if not mapping:
        return
    sdir = un / 'ppt/slides'
    # 两阶段改名避免互相覆盖
    for old in mapping:
        (sdir / old).rename(sdir / ('tmp_' + old))
        (sdir / '_rels' / (old + '.rels')).rename(sdir / '_rels' / ('tmp_' + old + '.rels'))
    for old, new in mapping.items():
        (sdir / ('tmp_' + old)).rename(sdir / new)
        (sdir / '_rels' / ('tmp_' + old + '.rels')).rename(sdir / '_rels' / (new + '.rels'))
    # 改所有 .rels 中对旧名的引用。两阶段（先占位符再落定）：
    # 置换是环形的（如 12→11、11→15），单阶段顺序替换会把改完的名字二次改写
    for rels in list((un / 'ppt/_rels').glob('*.rels')) + list(sdir.glob('_rels/*.rels')) + \
                list((un / 'ppt/notesSlides/_rels').glob('*.rels') if (un / 'ppt/notesSlides/_rels').exists() else []):
        x = x0 = rels.read_text(encoding='utf-8')
        for old in mapping:
            x = re.sub(r'(Target="(?:\.\./slides/|slides/)?)%s"' % re.escape(old), r'\g<1>__TMP__%s"' % old, x)
        for old, new in mapping.items():
            x = x.replace(f'__TMP__{old}"', f'{new}"')
        if x != x0:
            rels.write_text(x, encoding='utf-8')
    print('文件名重排:', ', '.join(f'{o}→{n}' for o, n in mapping.items()))


def top_level_elements(xml):
    """spTree 顶层元素 [(tag, start, end)]。"""
    tree_m = re.search(r'<p:spTree>.*</p:spTree>', xml, re.S)
    base = tree_m.start()
    tree = tree_m.group(0)
    out, depth, cur, start = [], 0, None, 0
    for m in re.finditer(r'<(/?)p:(sp|pic|grpSp|graphicFrame)(>| )', tree):
        tag, closing = m.group(2), m.group(1) == '/'
        if not closing and depth == 0:
            start, cur, depth = m.start(), tag, 1
        elif not closing and tag == cur:
            depth += 1
        elif closing and tag == cur and depth > 0:
            depth -= 1
            if depth == 0:
                out.append((cur, base + start, base + m.end()))
    return out


def ensure_rel(rels_xml, target):
    m = re.search(r'Id="(rId\d+)"[^>]*Type="%s"[^>]*Target="%s"' % (re.escape(SLIDE_REL), re.escape(target)), rels_xml)
    if not m:  # Target 在 Type 前的写法
        m = re.search(r'Id="(rId\d+)"[^>]*Target="%s"[^>]*Type="%s"' % (re.escape(target), re.escape(SLIDE_REL)), rels_xml)
    if m:
        return m.group(1), rels_xml
    maxr = max([int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)] or [0])
    rid = f'rId{maxr + 1}'
    rel = f'<Relationship Id="{rid}" Type="{SLIDE_REL}" Target="{target}"/>'
    return rid, rels_xml.replace('</Relationships>', rel + '</Relationships>')


def wire_edit(xml, span, rid):
    """返回把 span 内第一个 cNvPr 接上 hlink 的 (abs_pos, old, new)；已有链接则改目标。"""
    seg = xml[span[0]:span[1]]
    m = re.search(r'<p:cNvPr [^>]*?(/?)>', seg)
    open_tag = m.group(0)
    hlink = f'<a:hlinkClick r:id="{rid}" action="ppaction://hlinksldjump"/>'
    if m.group(1) == '/':  # 自闭合
        new = open_tag[:-2] + '>' + hlink + '</p:cNvPr>'
        return (span[0] + m.start(), open_tag, new)
    # 有子节点：替换已有 hlinkClick 或在开标签后插入
    end = seg.find('</p:cNvPr>', m.end())
    inner = seg[m.end():end]
    if 'hlinkClick' in inner:
        new_inner = re.sub(r'<a:hlinkClick [^>]*/>', hlink, inner, count=1)
    else:
        new_inner = hlink + inner
    return (span[0] + m.end(), inner, new_inner)


def apply_edits(xml, edits):
    for pos, old, new in sorted(edits, key=lambda e: -e[0]):
        assert xml[pos:pos + len(old)] == old
        xml = xml[:pos] + new + xml[pos + len(old):]
    return xml


def texts_of(xml, span):
    return re.findall(r'<a:t>([^<]*)</a:t>', xml[span[0]:span[1]])


def wire(un: Path, manual_map):
    renumber_slides(un)
    order = slide_order(un)
    info = {}
    for f in order:
        x = (un / 'ppt/slides' / f).read_text(encoding='utf-8')
        info[f] = x
    # 检测
    toc = next((f for f in order if '<a:t>目录</a:t>' in info[f]), None)
    dividers = {}  # 章节号 -> slide 文件
    for f in order:
        parts = re.findall(r'<a:t>PART\s*(\d+)</a:t>', info[f])
        if len(parts) == 1:
            dividers[int(parts[0])] = f
    for n, page in (manual_map or {}).items():
        dividers[n] = order[page - 1]
    contents = [f for f in order if '<a:t>导航一</a:t>' in info[f]]
    print(f'目录页: {toc} (第{order.index(toc)+1}页)' if toc else '⚠️ 未找到目录页')
    for n in sorted(dividers):
        print(f'章节{n} → {dividers[n]} (第{order.index(dividers[n])+1}页)')

    def chapter_of(texts):
        joined = '|'.join(texts)
        m = re.search(r'PART\s*(\d+)', joined)
        if m:
            return int(m.group(1))
        m = re.search(r'章节([一二三四五六七八九十])', joined)
        return CN.get(m.group(1)) if m else None

    total_links = 0
    for f in order:
        xml = info[f]
        rels_p = un / 'ppt/slides/_rels' / (f + '.rels')
        rels = rels_p.read_text(encoding='utf-8')
        edits = []

        if f == toc:  # 目录页：顶层元素按章节接线
            for tag, s, e in top_level_elements(xml):
                n = chapter_of(texts_of(xml, (s, e)))
                if n and n in dividers:
                    rid, rels = ensure_rel(rels, dividers[n])
                    edits.append(wire_edit(xml, (s, e), rid))
                    if tag == 'grpSp':
                        # WPS 不支持组合级超链接，组合内每个形状单独接线
                        for m in re.finditer(r'<p:(sp|pic)>.*?</p:\1>', xml[s:e], re.S):
                            edits.append(wire_edit(xml, (s + m.start(), s + m.end()), rid))
                elif n:
                    print(f'  ⚠️ {f}: 章节{n} 无转场页，跳过')
        elif f in contents:  # 内容页：导航条 + 页眉 logo
            # 导航容器 = 包含「导航一」的顶层元素（WPS 重存可能把标签包成嵌套子组合，
            # 不能用 rfind 找最近的 grpSp；正则扫 sp/pic 不受嵌套影响）
            gi = xml.find('<a:t>导航一</a:t>')
            gs, ge = next((s, e) for _, s, e in top_level_elements(xml) if s <= gi < e)
            grp = xml[gs:ge]
            last_para = None
            for m in re.finditer(r'<p:(sp|pic)>.*?</p:\1>', grp, re.S):
                seg, span = m.group(0), (gs + m.start(), gs + m.end())
                if m.group(1) == 'pic':  # 页眉 logo → 目录
                    if toc:
                        rid, rels = ensure_rel(rels, toc)
                        edits.append(wire_edit(xml, span, rid))
                    continue
                if 'prst="parallelogram"' in seg:
                    last_para = span
                    continue
                tm = re.search(r'<a:t>导航([一二三四五六七八九十])</a:t>', seg)
                if tm:
                    n = CN[tm.group(1)]
                    if n in dividers:
                        rid, rels = ensure_rel(rels, dividers[n])
                        edits.append(wire_edit(xml, span, rid))
                        if last_para:
                            edits.append(wire_edit(xml, last_para, rid))
                    else:
                        print(f'  ⚠️ {f}: 导航{tm.group(1)} 无转场页，跳过')
                    last_para = None
        if f in dividers.values() and toc:  # 转场页左上角 logo → 目录
            for tag, s, e in top_level_elements(xml):
                if tag == 'pic' and 'name="图片 21"' in xml[s:e]:
                    rid, rels = ensure_rel(rels, toc)
                    edits.append(wire_edit(xml, (s, e), rid))

        if edits:
            (un / 'ppt/slides' / f).write_text(apply_edits(xml, edits), encoding='utf-8')
            rels_p.write_text(rels, encoding='utf-8')
            total_links += len(edits)
            print(f'  {f}: +{len(edits)} 个链接')
    print(f'共接线 {total_links} 处')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='.pptx 文件或解包目录')
    ap.add_argument('--map', nargs='*', default=[], metavar='N=页码',
                    help='手动指定 章节号=显示页码，如 2=12')
    a = ap.parse_args()
    manual = {}
    for kv in a.map:
        k, v = kv.split('=')
        manual[int(k)] = int(v)
    t = Path(a.target)
    if t.is_dir():
        wire(t, manual)
        return
    # pptx：解压→接线→重打包（保留其余成员原样，含内嵌字体）
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with zipfile.ZipFile(t) as z:
            z.extractall(td)
        wire(td, manual)
        tmp_out = t.with_suffix('.pptx.tmp')
        with zipfile.ZipFile(t) as zin, zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, (td / item.filename).read_bytes())
        os.replace(tmp_out, t)
        print(f'已写回 {t}')


if __name__ == '__main__':
    main()
