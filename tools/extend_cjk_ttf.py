"""Append glyphs to the iPod's CJK.ttf (18px 4-bit EBDT strike, index fmt 1 / image fmt 1).

New bitmaps are rasterized from Hiragino Sans GB W6 -- the Simplified-Chinese member of the
Hiragino family CJK.ttf (Hiragino Kaku Gothic W6) was made from -- with the size/offset that best
matches the existing glyphs (see hiragino_raster.py). Existing glyphs are left untouched; new
ones are appended after the last glyph so the single index subtable just grows.

usage: extend_cjk_ttf.py <CJK.ttf in> <CJK.ttf out> <chars file (UTF-8 text)>
"""
import copy
import sys

from fontTools.ttLib import TTCollection, TTFont
from fontTools.ttLib.tables.BitmapGlyphMetrics import SmallGlyphMetrics
from fontTools.ttLib.tables.E_B_D_T_ import ebdt_bitmap_format_1

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from hiragino_raster import HIRAGINO, W6, raster  # noqa: E402

BASE = 16      # baseline row in the raster cell (BearingY = BASE - top)
ADVANCE = 18
TEMPLATE = 'uni6211'  # 我: source of placeholder outline / hmtx / LTSH values


def bitmap(ch):
    im = raster(ch)
    bbox = im.getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    im = im.crop(bbox)
    w, h = im.size
    px = im.load()
    data = bytearray()
    for y in range(h):
        row = bytearray((w + 1) // 2)
        for x in range(w):
            row[x // 2] |= px[x, y] << (4 if x % 2 == 0 else 0)
        data += row
    m = SmallGlyphMetrics()
    m.height, m.width, m.BearingX, m.BearingY, m.Advance = h, w, x0, BASE - y0, ADVANCE
    return m, bytes(data)


def main(src, dst, chars_path):
    font = TTFont(src, recalcTimestamp=False)  # keep head.modified: builds are reproducible
    cmap = font.getBestCmap()
    hira = TTCollection(HIRAGINO).fonts[W6].getBestCmap()
    wanted = []
    for ch in dict.fromkeys(open(chars_path, encoding='utf-8').read()):
        cp = ord(ch)
        if cp > 0xFFFF or cp in cmap or ch.isspace():
            continue
        if cp not in hira:
            print(f'skip {ch} U+{cp:04X}: not in Hiragino Sans GB')
            continue
        wanted.append(ch)

    order = font.getGlyphOrder()
    glyf, hmtx = font['glyf'], font['hmtx']
    ebdt = font['EBDT'].strikeData[0]
    strike = font['EBLC'].strikes[0]
    sub = strike.indexSubTables[-1]
    assert len(strike.indexSubTables) == 1 and sub.indexFormat == 1 and sub.imageFormat == 1
    fmt4 = [t for t in font['cmap'].tables if t.format == 4]
    # hdmx records are read-only glyph-name views; replace with plain dicts so we can append
    font['hdmx'].hdmx = {ppem: {n: w[n] for n in order} for ppem, w in font['hdmx'].hdmx.items()}
    hdmx = font['hdmx'].hdmx[18]
    ltsh = font['LTSH'].yPels

    added = 0
    for ch in wanted:
        r = bitmap(ch)
        if r is None:
            continue
        name = f'uni{ord(ch):04X}'
        order.append(name)
        glyf.glyphs[name] = copy.deepcopy(glyf[TEMPLATE])
        hmtx.metrics[name] = hmtx.metrics[TEMPLATE]
        hdmx[name] = ADVANCE
        ltsh[name] = ltsh[TEMPLATE]
        for t in fmt4:
            t.cmap[ord(ch)] = name
        g = ebdt_bitmap_format_1(b'', font)
        g.metrics, g.imageData = r
        ebdt[name] = g
        sub.names.append(name)
        added += 1

    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    sub.lastGlyphIndex = len(order) - 1
    strike.bitmapSizeTable.endGlyphIndex = len(order) - 1
    font.save(dst)
    print(f'added {added} glyphs ({len(wanted) - added} empty); now {len(order)} glyphs')


if __name__ == '__main__':
    main(*sys.argv[1:4])
