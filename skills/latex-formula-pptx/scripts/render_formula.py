#!/usr/bin/env python3
"""LaTeX 公式 → 透明底 PNG 渲染管线。

用法:
    python3 render_formula.py 'P_f = \\int_\\Omega I[g(x)\\le 0]\\, f_X(x)\\,dx' out.png \\
        --color 1F2937 --dpi 600 [--display]

管线: pdflatex (standalone+amsmath) → pdftoppm 高分辨率 PNG → Pillow 以灰度为
alpha 蒙版填充目标色 → 紧裁透明底 PNG。
颜色规则: 浅底用深色(如 1F2937/000000)，深底/照片底用 FFFFFF。
缺宏包时: tlmgr install <pkg>（TinyTeX 用户级安装，无需 sudo）。
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

TEMPLATE = r"""\documentclass[border=2pt]{standalone}
\usepackage{amsmath,amssymb}
\begin{document}
%(body)s
\end{document}
"""


def render(latex, out_png, color='000000', dpi=600, display=False):
    body = ('$\\displaystyle ' if display else '$') + latex + '$'
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / 'f.tex').write_text(TEMPLATE % {'body': body}, encoding='utf-8')
        r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'f.tex'],
                           cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            tail = '\n'.join(r.stdout.splitlines()[-25:])
            sys.exit(f'pdflatex 失败（若提示缺 .sty/.cls，先 tlmgr install 对应包）:\n{tail}')
        subprocess.run(['pdftoppm', '-png', '-r', str(dpi), str(td / 'f.pdf'), str(td / 'p')], check=True)
        img = Image.open(next(td.glob('p*.png')))
        # 灰度反相作为 alpha：黑墨=不透明，白底=透明，边缘平滑保留
        g = img.convert('L')
        alpha = g.point(lambda v: 255 - v)
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        out = Image.new('RGBA', img.size, rgb + (0,))
        out.putalpha(alpha)
        out = out.crop(alpha.getbbox())
        out.save(out_png)
        print(f'{out_png}  {out.size[0]}x{out.size[1]}px  color=#{color}  dpi={dpi}')
        return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('latex')
    ap.add_argument('out')
    ap.add_argument('--color', default='000000', help='十六进制色，如 1F2937 / FFFFFF / 254AA5')
    ap.add_argument('--dpi', type=int, default=600)
    ap.add_argument('--display', action='store_true', help='display 样式（大型运算符/分式）')
    a = ap.parse_args()
    render(a.latex, a.out, a.color, a.dpi, a.display)
