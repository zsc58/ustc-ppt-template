#!/usr/bin/env python3
"""USTB → USTC 模版改造：颜色、媒体、背景轮换、文字占位化（在解包目录上操作）。"""
import re, shutil
from pathlib import Path

UN = Path('/tmp/ustc_work/unpacked')
ASSETS = Path('./work')
REPL = ASSETS / 'media_replacements'

# ---------- 1. 全局颜色替换 ----------
COLOR_MAP = {
    '005B94': '254AA5',  # 主色 USTB蓝 -> 科大蓝(ustc_logo.pdf 实测)
    '00ACFC': '4D74C8',  # 亮蓝强调
    'ECF5FB': 'ECF0FA',  # 浅蓝底
    'B3D4E8': 'BCC9E8',  # 浅蓝辅助
    '77D7FF': '92ADEC',  # 高亮点缀
}
THEME_MAP = {'4874CB': '254AA5'}  # WPS 默认 accent1 -> 科大蓝

def sub_colors(path, mapping):
    xml = path.read_text(encoding='utf-8')
    orig = xml
    for old, new in mapping.items():
        xml = xml.replace(f'val="{old}"', f'val="{new}"')
    if xml != orig:
        path.write_text(xml, encoding='utf-8')
        return True
    return False

n = 0
for d in ['ppt/slides', 'ppt/slideLayouts', 'ppt/slideMasters', 'ppt/notesMasters', 'ppt/handoutMasters']:
    for f in (UN / d).glob('*.xml'):
        n += sub_colors(f, COLOR_MAP)
for f in (UN / 'ppt/theme').glob('*.xml'):
    n += sub_colors(f, THEME_MAP)
print(f'color-replaced files: {n}')

# ---------- 2. 媒体替换（同名覆盖） ----------
for f in REPL.iterdir():
    shutil.copy(f, UN / 'ppt/media' / f.name)
    print('media <-', f.name)

# ---------- 3. 背景照片轮换 ----------
# 新增媒体并改 rels：slide2->湖景, slide3->樱花, slide5->老建筑（slide1/4 保持封面照 image5）
ROTATE = {
    'slide2.xml.rels': ('bg_toc.jpg', 'image30.jpeg'),
    'slide3.xml.rels': ('bg_section.jpg', 'image31.jpeg'),
    'slide5.xml.rels': ('bg_thanks.jpg', 'image32.jpeg'),
}
for rels_name, (src, dst) in ROTATE.items():
    shutil.copy(ASSETS / src, UN / 'ppt/media' / dst)
    rels = UN / 'ppt/slides/_rels' / rels_name
    xml = rels.read_text(encoding='utf-8')
    xml2 = xml.replace('Target="../media/image5.jpeg"', f'Target="../media/{dst}"')
    assert xml2 != xml, f'no image5 ref in {rels_name}'
    rels.write_text(xml2, encoding='utf-8')
    print(f'{rels_name}: image5.jpeg -> {dst}')

# ---------- 4. 示例文字占位化 ----------
TEXT_MAP_S4 = [
    ('问题定位：逆可靠度分析', '要点卡片一：问题定位'),
    ('• 已知目标失效概率 ', '• 要点描述示例：已知 '),
    ('，反求阈值 ', '，求解目标 '),
    ('• 正向分析关心 ', '• 对比示例：正向关心 '),
    ('，逆向分析关心 ', '，逆向关心 '),
    ('• 传统 MCS + Kriging 在小 ', '• 难点示例：传统方法在小 '),
    (' 下样本量爆炸', ' 下成本急剧上升'),
    ('• 需要主动学习 + IS 联合策略压缩成本', '• 思路示例：用联合策略压缩计算成本'),
    ('AK-IRs 的两条主线', '要点卡片二：方法主线'),
    ('• AK-IR1：纯 MCS 撒点 + UIR 主动学习选点', '• 方法一：基础策略（示例文字，请替换）'),
    ('• AK-IR2：SQP 粗定位 iMPP + IS 重要抽样 + UIR', '• 方法二：改进策略（示例文字，请替换）'),
    ('→ AK-IR2 把样本量从 N_MCS ≥ 10⁶ 压到 N_IS = 10⁴ 量级', '→ 结论示例：样本量从 10⁶ 压缩到 10⁴ 量级'),
    ('• 算例 3 (', '• 数据支撑示例 ('),
    (' ≈ 3.998×10⁻⁴) 验证小失效概率下有效', ' ≈ 3.998×10⁻⁴) 说明方法有效'),
    ('SQP → iMPP', '步骤一'),
    ('  ≤ 20 次调用，定位 IS 中心', '  步骤说明（示例文字）'),
    ('生成 IS 池', '步骤二'),
    ('  以 iMPP 为均值，N_IS = 10⁴', '  步骤说明（示例文字）'),
    ('建初始 Kriging', '步骤三'),
    ('  SQP 路径点直接复用为 TP', '  步骤说明（示例文字）'),
    ('UIR 主动学习', '步骤四'),
    ('  选点 → 更新 → 判停 U_IR ≥ 2', '  步骤说明（示例文字）'),
    ('选 ', '结论条示例：选 '),
]
TEXT_MAP_S5 = [
    ('汇报人：张熙晨', '汇报人：（姓名）'),
    ('2026 年 5 月 25 日', '（  年   月   日）'),
]

def sub_texts(path, pairs):
    xml = path.read_text(encoding='utf-8')
    cnt = 0
    for old, new in pairs:
        o, nw = f'<a:t>{old}</a:t>', f'<a:t>{new}</a:t>'
        if o in xml:
            xml = xml.replace(o, nw)
            cnt += 1
    path.write_text(xml, encoding='utf-8')
    return cnt

c4 = sub_texts(UN / 'ppt/slides/slide4.xml', TEXT_MAP_S4)
c5 = sub_texts(UN / 'ppt/slides/slide5.xml', TEXT_MAP_S5)
print(f'slide4 text replaced: {c4}/{len(TEXT_MAP_S4)}, slide5: {c5}/{len(TEXT_MAP_S5)}')

# ---------- 5. 残留检查 ----------
left = []
for d in ['ppt/slides', 'ppt/slideLayouts', 'ppt/slideMasters']:
    for f in (UN / d).glob('*.xml'):
        x = f.read_text(encoding='utf-8')
        for c in COLOR_MAP:
            if c in x:
                left.append((f.name, c))
print('color leftovers:', left or 'none')
