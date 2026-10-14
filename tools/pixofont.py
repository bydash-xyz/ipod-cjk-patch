"""Parser for the bitmap fonts compiled into the iPod 5G/5.5G `osos` image.

Layout (little endian), per iPodWizard's Font.h:
  HEADER1  magic(04 00 21 00) first_char last_char 1 numChars numGroups(u32)
  groups   [code u16, charIndexOffset u16, length u32] * numGroups
  HEADER2  w1 u16, name[66], size u32, style u8, bitdepth u8, numChars u16,
           flags u16, width u16, line_height u16, descent u16, w4 u32,
           finfo_size u32, charMapEnd u32, metricsEnd u32
  charmap  u16 * numChars   (char index -> metric index)
  (align 4)
  metrics  [offset1 u16, offset2 u16, width i16, ident i16]  (u32 offsets when bitdepth==2)
  bitmap   header: w1 u32, height u16, rowPixels u16, rowBytes u16, bitDepth u16, w2 u32, len u32
           data: height rows of rowBytes; glyph i occupies columns [offset1, offset2)
"""
import re
import struct
import sys

from PIL import Image

H2 = struct.Struct('<H66sIBBHHHHHIIII')


class PixoFont:
    def __init__(self, buf, off):
        self.off = off
        p = off
        magic, self.first, self.last, _one, self.nchars, ngroups = struct.unpack_from('<4sHHHHI', buf, p)
        if ngroups == 0 or ngroups > 0x2000 or self.nchars == 0:
            raise ValueError('bad header')
        p += 16
        self.groups = [struct.unpack_from('<HHI', buf, p + 8 * i) for i in range(ngroups)]
        p += 8 * ngroups
        self.h2_off = p
        (self.w1, name, self.size, self.style, self.depth, nchars2, self.flags, self.width,
         self.line_height, self.descent, self.w4, self.finfo_size, self.charmap_end,
         self.metrics_end) = H2.unpack_from(buf, p)
        if nchars2 != self.nchars or self.depth not in (1, 2, 4, 8):
            raise ValueError('bad header2')
        self.name = name.split(b'\0')[0].decode('latin1')
        p += H2.size
        self.charmap_off = p
        self.charmap = struct.unpack_from('<%dH' % self.nchars, buf, p)
        p += 2 * self.nchars
        p = (p - off + 3) // 4 * 4 + off
        wide = self.depth == 2
        msize = 12 if wide else 8
        nmetrics = (self.metrics_end - self.charmap_end) // msize
        self.metrics_off = p
        self.fixed = bool(self.flags & 1)
        fmt = '<IIhh' if wide else '<HHhh'
        self.metrics = [struct.unpack_from(fmt, buf, p + msize * i) for i in range(nmetrics)]
        p += msize * nmetrics
        if wide:
            _d1, self.height, self.row_pixels, self.row_bytes = struct.unpack_from('<8sIII', buf, p)
            p += 32
        else:
            (_w1, self.height, self.row_pixels, self.row_bytes, _bd, _w2,
             _len) = struct.unpack_from('<IHHHHII', buf, p)
            p += 20
        if not 0 < self.height <= 80:
            raise ValueError('bad bitmap header')
        self.bitmap_off = p
        self.end = p + self.height * self.row_bytes
        self.buf = buf

    # --- lookups -----------------------------------------------------------
    def char_index(self, cp):
        for code, idx, length in self.groups:
            if code <= cp < code + length:
                return idx + cp - code - 1  # group offsets are 1-based
        return None

    def codepoints(self):
        for code, _idx, length in self.groups:
            yield from range(code, code + length)

    def glyph(self, cp):
        ci = self.char_index(cp)
        if ci is None or ci >= self.nchars:
            return None
        mi = self.charmap[ci]
        if self.fixed:
            o1, o2, width, ident = mi * self.size, (mi + 1) * self.size, self.size, 0
        elif mi < len(self.metrics):
            o1, o2, width, ident = self.metrics[mi]
        else:
            return None
        w = o2 - o1
        img = Image.new('L', (max(w, 1), self.height), 0)
        px = img.load()
        maxv = (1 << self.depth) - 1
        per = 8 // self.depth if self.depth < 8 else 1
        for y in range(self.height):
            row = self.bitmap_off + y * self.row_bytes
            for x in range(w):
                X = o1 + x
                if self.depth == 8:
                    v = self.buf[row + X]
                else:
                    byte = self.buf[row + X // per]
                    # pixels are packed MSB-first
                    shift = 8 - self.depth - (X % per) * self.depth
                    v = (byte >> shift) & maxv
                px[x, y] = v * 255 // maxv
        return img, width, ident

    def render(self, text, scale=4):
        parts = [self.glyph(ord(c)) for c in text]
        W = sum((g[1] if g else 6) for g in parts) + 8
        canvas = Image.new('L', (W, self.height + 4), 0)
        x = 4
        for g in parts:
            if g is None:
                x += 6
                continue
            img, width, ident = g
            canvas.paste(img, (x + ident, 2))
            x += width
        return canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)

    def summary(self):
        cps = list(self.codepoints())
        han = sum(1 for c in cps if 0x4E00 <= c <= 0x9FFF)
        kana = sum(1 for c in cps if 0x3040 <= c <= 0x30FF)
        hangul = sum(1 for c in cps if 0xAC00 <= c <= 0xD7AF)
        return (f'{self.off:#09x} len={self.end - self.off:#08x} name={self.name!r:28} size={self.size:2d} '
                f'style={self.style} depth={self.depth} h={self.height:2d} lineh={self.line_height} '
                f'desc={self.descent} chars={self.nchars:5d} han={han:5d} kana={kana:3d} hangul={hangul:5d}')


def scan(buf, start=0, end=None):
    end = end or len(buf)
    fonts = []
    for m in re.finditer(rb'[\x04\x05]\x00\x21\x00', buf[start:end]):
        try:
            fonts.append(PixoFont(buf, start + m.start()))
        except (ValueError, struct.error):
            pass
    return fonts


# --- building ----------------------------------------------------------------
def serialize(f, groups=None, charmap=None, metrics=None, columns=None):
    """Re-encode font `f`, optionally with new tables.

    groups:  [(code, charIndexOffset(1-based), length)]
    charmap: [glyph index per char index]
    metrics: [(offset1, offset2, width, ident)] for variable-width fonts
    columns: list of per-glyph bitmaps as (pixel_columns) -> raw packed rows built here
             given as list of lists of column bitmasks? (see subset()) -- None keeps original.
    """
    groups = f.groups if groups is None else groups
    charmap = list(f.charmap) if charmap is None else charmap
    metrics = f.metrics if metrics is None else metrics
    if columns is None:
        rows = [f.buf[f.bitmap_off + y * f.row_bytes:f.bitmap_off + (y + 1) * f.row_bytes]
                for y in range(f.height)]
        row_pixels = f.row_pixels
    else:
        rows, row_pixels = columns
    row_bytes = len(rows[0])
    nchars = len(charmap)
    cps = [c for code, _i, ln in groups for c in range(code, code + ln)]
    out = bytearray()
    out += f.buf[f.off:f.off + 4]
    out += struct.pack('<HHHHI', min(cps), max(cps), 1, nchars, len(groups))
    for g in groups:
        out += struct.pack('<HHI', *g)
    h2 = len(out)
    name = f.buf[f.h2_off + 2:f.h2_off + 68]
    out += b'\0' * H2.size  # placeholder
    out += struct.pack('<%dH' % nchars, *charmap)
    while (len(out)) % 4:
        out += b'\0'
    charmap_end = len(out) - h2
    wide = f.depth == 2
    if not f.fixed:
        for m in metrics:
            out += struct.pack('<IIhh' if wide else '<HHhh', *m)
    metrics_end = len(out) - h2
    H2.pack_into(out, h2, f.w1, name, f.size, f.style, f.depth, nchars, f.flags, f.width,
                 f.line_height, f.descent, f.w4, f.finfo_size, charmap_end, metrics_end)
    if wide:
        raise NotImplementedError('2-bit fonts')
    hdr = f.buf[f.bitmap_off - 20:f.bitmap_off]
    w1, _h, _rp, _rb, bd, w2, _len = struct.unpack('<IHHHHII', hdr)
    out += struct.pack('<IHHHHII', w1, f.height, row_pixels, row_bytes, bd, w2, f.height * row_bytes)
    for r in rows:
        out += r
    return bytes(out), h2


def get_px(f, X, y):
    per = 8 // f.depth
    byte = f.buf[f.bitmap_off + y * f.row_bytes + X // per]
    return (byte >> (8 - f.depth - (X % per) * f.depth)) & ((1 << f.depth) - 1)


def subset(f, keep, shift=None, extra=None):
    """Rebuild `f` keeping only codepoints for which keep(cp) is true. Returns (bytes, h2_offset).

    shift(cp) -> dy moves that char's glyph down by dy rows (glyphs shared by several chars
    take the shift of the first one).
    extra: {cp: ('alias', target_cp) | ('image', PIL 'L' image f.size x f.height, 255 = ink)}
    adds characters -- an alias reuses the glyph of a kept char in this font; images need a
    fixed-width font."""
    extra = extra or {}
    glyph_new = {}   # source key -> new glyph index
    order = []       # new glyph index -> ('orig', g, dy) | ('image', im)
    chars = {}       # cp -> new glyph index
    for code, idx, ln in f.groups:
        for k in range(ln):
            cp = code + k
            if not keep(cp) or cp in extra:
                continue
            g = f.charmap[idx + k - 1]
            if ('orig', g) not in glyph_new:
                glyph_new[('orig', g)] = len(order)
                order.append(('orig', g, shift(cp) if shift else 0))
            chars[cp] = glyph_new[('orig', g)]
    for cp, (kind, src) in sorted(extra.items()):
        if kind == 'image':
            assert f.fixed and src.size == (f.size, f.height), f'{f.name}: bad image for U+{cp:04X}'
            chars[cp] = len(order)
            order.append(('image', src))
    for cp, (kind, src) in sorted(extra.items()):  # aliases after images so targets exist
        if kind == 'alias':
            assert src in chars, f'{f.name}: alias target U+{src:04X} not in font'
            chars[cp] = chars[src]
    if not chars:  # a font must keep >= 1 char: park its first glyph on an unused PUA codepoint
        code, idx, _ln = f.groups[0]
        glyph_new[('orig', f.charmap[idx - 1])] = 0
        order.append(('orig', f.charmap[idx - 1], 0))
        chars[0xE000] = 0
    groups, charmap = [], []
    for cp in sorted(chars):
        if groups and groups[-1][0] + groups[-1][2] == cp:
            groups[-1][2] += 1
        else:
            groups.append([cp, len(charmap) + 1, 1])
        charmap.append(chars[cp])
    widths = [f.size if (f.fixed or o[0] == 'image') else f.metrics[o[1]][1] - f.metrics[o[1]][0]
              for o in order]
    total = sum(widths)
    per = 8 // f.depth
    maxv = (1 << f.depth) - 1
    row_bytes = ((total + per - 1) // per + 3) // 4 * 4
    rows = [bytearray(row_bytes) for _ in range(f.height)]
    metrics = []

    def put(x, y, v):
        rows[y][x // per] |= v << (8 - f.depth - (x % per) * f.depth)

    x = 0
    for o, w in zip(order, widths):
        if o[0] == 'image':
            px = o[1].load()
            for X in range(w):
                for y in range(f.height):
                    if px[X, y]:
                        put(x + X, y, px[X, y] * maxv // 255)
        else:
            _k, g, dy = o
            o1 = g * f.size if f.fixed else f.metrics[g][0]
            for X in range(w):
                for y in range(f.height):
                    v = get_px(f, o1 + X, y)
                    if v:
                        assert 0 <= y + dy < f.height, f'{f.name}: shift would clip glyph'
                        put(x + X, y + dy, v)
            if not f.fixed:
                _o1, _o2, mw, ident = f.metrics[g]
                metrics.append((x, x + w, mw, ident))
        x += w
    return serialize(f, [tuple(g) for g in groups], charmap, metrics, ([bytes(r) for r in rows], total))


if __name__ == '__main__':
    # usage: pixofont.py <firmware file>  -- list the bitmap fonts in its osos image
    sys.path.insert(0, __file__.rsplit('/', 1)[0])
    import ipodfw
    data = open(sys.argv[1], 'rb').read()
    for f in scan(data, *ipodfw.data_range(data, 'osos')):
        print(f.summary())
