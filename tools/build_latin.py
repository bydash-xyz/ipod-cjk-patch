"""Redraw Podium Sans 16, which lyrics use for Latin text and symbols, from Fusion Pixel 12px.

Lyrics are drawn with the osos bitmap font Podium Sans 16 (bold, 4-bit antialiased) first; only
characters it lacks fall back to the 12px CJK fonts. On the device its 13px-tall bold brackets
and parentheses sit next to Fusion Pixel's thin 11px Han like a second typeface. Here every
Podium Sans 16 glyph is redrawn from Fusion Pixel 12px proportional (OFL), and the symbols stock
only has in the CJK families (♪ ★ ① ※ box drawing, ...) are added, so they too come from one
font in one style.

The firmware lines up mixed fonts by the bottom of their glyph cells: in an on-device photo,
Podium Sans 16's parentheses (cell rows 2..14 of 17) end on the same row as Fusion's Han (rows
2..12 of Hei's 15). So Podium Sans keeps its header, and Fusion glyphs go 2 rows lower than in the
Hei cells build_unified.py writes, which puts Han on rows 4..14 and Latin on Fusion's baseline.

Chars Fusion lacks: NFKC compositions are drawn from their parts (ﬁ -> f i), the rest are copied
from stock Hei or Osaka (regular-weight 1-bit, bottom-aligned the same way), and only then kept
from Podium Sans.

usage: build_latin.py <stock Firmware-25.6.3> <fusion bdf dir> <out.png>  (sheet of the glyphs)
"""
import sys
import unicodedata

from PIL import Image

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from bdf import load, to_image  # noqa: E402
from pixofont import subset  # noqa: E402

TARGET = ('Podium Sans', 16)
HEI_HEIGHT, HEI_BASELINE = 15, 12  # Hei cell row under the proportional Fusion baseline (Han -> 2..12)
CJK_FAMILIES = ('AppleGothic', 'AppleLiGothicMedium', 'Hei', 'Osaka')
COPY_FROM = ('Hei', 'Osaka')  # regular-weight 1-bit Latin
ALIASES = {0x02BB: 0x2018, 0x02BC: 0x2019}  # modifier-letter commas Fusion lacks -> ‘ ’


def is_target_font(f):
    return (f.name, f.size) == TARGET


def bdf_glyph(g, height):
    """Fusion BDF glyph -> (image of the cell's height or None, advance, x offset)."""
    im, ox, oy, dw = to_image(g)
    if im.getbbox() is None:
        return None, dw, 0
    top = HEI_BASELINE + height - HEI_HEIGHT - (oy + im.height)  # cells are bottom-aligned
    assert top >= 0 and top + im.height <= height, 'glyph does not fit the cell'
    cell = Image.new('L', (im.width, height), 0)
    cell.paste(im, (0, top))
    return cell, dw, ox


def compose(parts, height):
    """Draw a sequence of (image, advance, x offset) glyphs as one glyph."""
    width = sum(adv for _im, adv, _ox in parts)
    cell = Image.new('L', (max(width, 1), height), 0)
    x = 0
    for im, adv, ox in parts:
        if im:
            cell.paste(im, (x + ox, 0))
        x += adv
    bb = cell.getbbox()
    if bb is None:
        return None, width, 0
    return cell.crop((bb[0], 0, bb[2], height)), width, bb[0]


def stock_glyph(f, cp, height):
    """Copy a stock bitmap glyph into a cell of `height` rows, bottoms aligned."""
    img, advance, ident = f.glyph(cp)
    bb = img.getbbox()
    if bb is None:
        return None, advance, ident
    dy = height - f.height
    assert bb[1] + dy >= 0, f'{f.name} U+{cp:04X} does not fit'
    cell = Image.new('L', (img.width, height), 0)
    cell.paste(img, (0, dy))
    return cell, advance, ident


def glyphs(fonts, fusion_dir, is_cjk, extra=()):
    """{cp: ('glyph', (image, advance, x offset))} for the new font, and counts per source.

    fonts: the stock firmware's bitmap fonts; is_cjk(cp): chars build_unified.py puts in Hei;
    extra: more chars to add (from charsets/lyrics_extra.txt) when Fusion has them."""
    target = next(f for f in fonts if is_target_font(f))
    base = {f.name: f for f in fonts if f.size == 12 and f.name in COPY_FROM}
    h = target.height
    fusion = {v: load(f'{fusion_dir}/fusion-pixel-12px-proportional-{v}.bdf')[0] for v in ('latin', 'zh_hans')}
    own = set(target.codepoints())
    # symbols only the CJK families have: add them when Fusion can draw them
    added = {cp for cp in {cp for f in fonts if f.size == 12 and f.name.split('_')[0] in CJK_FAMILIES
                           for cp in f.codepoints() if cp < 0x3000} | set(extra)
             if cp not in own and not is_cjk(cp) and (cp in fusion['latin'] or cp in fusion['zh_hans'])}

    def from_fusion(cp):
        if 0xE000 <= cp <= 0xF8FF:  # Apple's private UI glyphs (icons, digit styles) stay
            return None
        # Latin and anything the font had: Latin forms (’ is half-width); added symbols:
        # the zh_hans forms, full-width like the CJK fonts they come from
        order = ('latin', 'zh_hans') if cp in own or cp < 0x2000 else ('zh_hans', 'latin')
        cp = ALIASES.get(cp, cp)
        g = next((fusion[v][cp] for v in order if cp in fusion[v]), None)
        return g and bdf_glyph(g, h)

    out, source = {}, {}
    for cp in sorted(own | added):
        g = from_fusion(cp)
        src = 'Fusion Pixel'
        if g is None and not 0xE000 <= cp <= 0xF8FF:
            parts = unicodedata.normalize('NFKC', chr(cp))
            if len(parts) > 1 and all(ord(c) in fusion['latin'] for c in parts):
                g, src = compose([from_fusion(ord(c)) for c in parts], h), 'composed'
        if g is None:
            f = None if 0xE000 <= cp <= 0xF8FF else next(
                (base[n] for n in COPY_FROM if base[n].char_index(cp) is not None), None)
            if f is None:
                f, g = target, target.glyph(cp)
            else:
                g = stock_glyph(f, cp, h)
            src = f'stock {f.name}'
        assert g[1] <= target.width, f'U+{cp:04X} wider than {target.width}px'
        out[cp] = ('glyph', g)
        source[src] = source.get(src, 0) + 1
    return out, source


def rebuild(fonts, fusion_dir, is_cjk, extra=()):
    """(font blob, header2 offset) of the new Podium Sans 16; it keeps the stock header."""
    target = next(f for f in fonts if is_target_font(f))
    new, source = glyphs(fonts, fusion_dir, is_cjk, extra)
    print(f'{target.name} {target.size}: {len(new)} chars ('
          + ', '.join(f'{n} from {s}' for s, n in source.items()) + ')')
    return subset(target, lambda cp: False, None, new)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    import ipodfw
    from build_unified import is_target
    from pixofont import scan
    fw = open(sys.argv[1], 'rb').read()
    blob, _h2 = rebuild(scan(fw, *ipodfw.data_range(fw, 'osos')), sys.argv[2], is_target)
    new = scan(blob)[0]
    cps = list(new.codepoints())
    cols = 64
    sheet = Image.new('L', (cols * 14, -(-len(cps) // cols) * (new.height + 2)), 255)
    for i, cp in enumerate(cps):
        img, _adv, ident = new.glyph(cp)
        sheet.paste(0, (i % cols * 14 + max(ident, 0), i // cols * (new.height + 2)), img)
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(sys.argv[3])
    print(f'wrote {sys.argv[3]}')
