"""Minimal BDF reader: {codepoint: (bbx_w, bbx_h, off_x, off_y, dwidth, rows-as-ints)}."""


def load(path):
    glyphs = {}
    ascent = descent = None
    with open(path, encoding='latin1') as f:
        cp = rows = None
        for line in f:
            if line.startswith('FONT_ASCENT'):
                ascent = int(line.split()[1])
            elif line.startswith('FONT_DESCENT'):
                descent = int(line.split()[1])
            elif line.startswith('ENCODING'):
                cp = int(line.split()[1])
            elif line.startswith('DWIDTH'):
                dw = int(line.split()[1])
            elif line.startswith('BBX'):
                w, h, ox, oy = map(int, line.split()[1:5])
            elif line.startswith('BITMAP'):
                rows = []
            elif line.startswith('ENDCHAR'):
                glyphs[cp] = (w, h, ox, oy, dw, rows)
                cp = rows = None
            elif rows is not None and line.strip():
                rows.append(int(line.strip(), 16))
    return glyphs, ascent, descent


def to_image(g):
    """Return (PIL 'L' image of the BBX (255=ink), off_x, off_y, dwidth)."""
    from PIL import Image
    w, h, ox, oy, dw, rows = g
    im = Image.new('L', (max(w, 1), max(h, 1)), 0)
    px = im.load()
    nbits = ((w + 7) // 8) * 8
    for y, r in enumerate(rows):
        for x in range(w):
            if r >> (nbits - 1 - x) & 1:
                px[x, y] = 255
    return im, ox, oy, dw
