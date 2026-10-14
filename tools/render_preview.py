"""Render a before/after image of CJK text from two firmware files' own fonts.

Lyrics are drawn with the 12px bitmap fonts in the osos image. Each char takes the first font in
the firmware's font registry that has it, on a shared baseline. This models stock behaviour; the
real stock lookup order is not exactly registry order, but on the patched firmware every CJK char
has one source, so order doesn't matter there. Menu text is drawn from CJK.ttf's 18px strike,
with chars it lacks falling back to the 12px bitmap fonts, as on the device.

usage: render_preview.py <stock firmware> <patched firmware> <out.png>
"""
import io
import struct
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import ipodfw  # noqa: E402
from build_rsrc import read_file  # noqa: E402
from pixofont import scan  # noqa: E402

REGISTRY = (0x6a6480, 0x6a6660)
LYRICS = [
    '再也不愿意 让你偷偷的溜走',
    '问姑娘何时能回首',
    '妳說過會一直愛我嗎',
    '夕暮れが僕のドアをノックする',
    '사랑해요 我爱你',
    '(合)嗨啊啰哩 嘢 哋 嘅',
]
MENU = ['汪苏泷 - 达达乐队', '犸嫫恓 字体测试']
SCALE = 3
INK, PAPER, MUTED, GUIDE = (20, 20, 20), (250, 250, 248), (120, 120, 120), (255, 196, 196)


class Firmware:
    def __init__(self, path):
        fw = open(path, 'rb').read()
        a, b = ipodfw.data_range(fw, 'osos')

        def pos(f):
            return next((o for o in range(*REGISTRY, 4)
                         if struct.unpack_from('<II', fw, o) == (f.off - a, f.h2_off - a)), None)
        fonts = [(pos(f), f) for f in scan(fw, a, b) if f.size == 12]
        self.fonts = [f for p, f in sorted((p, f) for p, f in fonts if p is not None)]
        ttf = TTFont(io.BytesIO(read_file(fw, '/Resources/Fonts/CJK.ttf')))
        self.cmap = ttf.getBestCmap()
        self.strike = ttf['EBDT'].strikeData[0]

    def bitmap_glyph(self, ch):
        """(image, advance, x offset, rows above baseline) from the first 12px font with `ch`."""
        f = next((f for f in self.fonts if f.char_index(ord(ch)) is not None), None)
        g = f and f.glyph(ord(ch))
        if not g:
            return None
        img, width, ident = g
        return img, width, ident, f.height - f.descent

    def ttf_glyph(self, ch):
        """(image, advance, x offset, rows above baseline) from CJK.ttf's 18px 4-bit strike."""
        name = self.cmap.get(ord(ch))
        if name is None or name not in self.strike:
            return None
        g = self.strike[name]
        g.ensureDecompiled()
        m = g.metrics
        img = Image.new('L', (max(m.width, 1), max(m.height, 1)), 0)
        stride = (m.width + 1) // 2
        for y in range(m.height):
            for x in range(m.width):
                b = g.imageData[y * stride + x // 2]
                img.putpixel((x, y), ((b >> 4) if x % 2 == 0 else (b & 15)) * 17)
        return img, m.Advance, m.BearingX, m.BearingY


def draw_line(text, glyph, baseline, height, guide=False):
    """Draw `text` on a white strip with its baseline at row `baseline`. guide=True tints the row
    just below the baseline, so a glyph that drops 1px stands out."""
    parts = [glyph(ch) if not ch.isspace() else None for ch in text]
    width = sum(p[1] if p else 6 for p in parts) + 4
    ink = Image.new('L', (width, height), 0)
    x = 2
    for p in parts:
        if p is None:
            x += 6
            continue
        img, adv, dx, above = p
        ink.paste(img, (x + dx, baseline - above), img)
        x += adv
    strip = Image.new('RGB', ink.size, PAPER)
    if guide:
        ImageDraw.Draw(strip).line([(0, baseline + 1), (width, baseline + 1)], fill=GUIDE)
    strip.paste(Image.new('RGB', ink.size, INK), (0, 0), ink)
    return strip


def main(stock_path, patched_path, out):
    firmwares = [('Stock 1.3', Firmware(stock_path)), ('Patched', Firmware(patched_path))]
    columns = []
    for label, fw in firmwares:
        def menu_glyph(ch, fw=fw):
            return fw.ttf_glyph(ch) or fw.bitmap_glyph(ch)
        rows = [draw_line(t, menu_glyph, 17, 22) for t in MENU] + [None]
        rows += [draw_line(t, fw.bitmap_glyph, 12, 17, guide=True) for t in LYRICS]
        columns.append((label, rows))

    pad, gap, title_h, section_h = 16, 32, 28, 20
    label_font = ImageFont.load_default(size=16)
    small = ImageFont.load_default(size=12)
    col_w = max(r.width for _l, rows in columns for r in rows if r) * SCALE
    body_h = sum((r.height * SCALE + 4) if r else section_h for r in columns[0][1])
    W = pad * 2 + col_w * 2 + gap
    H = pad + title_h + section_h + body_h + pad
    canvas = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(canvas)
    for i, (label, rows) in enumerate(columns):
        x = pad + i * (col_w + gap)
        d.text((x, pad), label, fill=INK, font=label_font)
        y = pad + title_h
        d.text((x, y), 'Menus (CJK.ttf)', fill=MUTED, font=small)
        y += section_h
        for r in rows:
            if r is None:
                d.text((x, y + 2), 'Lyrics (12px bitmap fonts; red rule = 1px below the baseline)',
                       fill=MUTED, font=small)
                y += section_h
                continue
            canvas.paste(r.resize((r.width * SCALE, r.height * SCALE), Image.NEAREST), (x, y))
            y += r.height * SCALE + 4
    canvas.save(out, optimize=True)
    print(f'wrote {out} ({W}x{H})')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:4])
