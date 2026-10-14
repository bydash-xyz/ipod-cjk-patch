"""Rasterize glyphs from Hiragino Sans GB W6 to match CJK.ttf's 18px 4-bit EBDT strike."""
import os

from PIL import Image, ImageDraw, ImageFont

HIRAGINO = '/System/Library/Fonts/Hiragino Sans GB.ttc'
W6 = 2  # face index in the collection
if not os.path.exists(HIRAGINO):
    raise SystemExit(f'{HIRAGINO} not found: the menu font build needs macOS (Hiragino Sans GB)')


def raster(ch, size=18.0, dx=0, base=16, cell=20, face=W6):
    """Return a cell x cell 'L' image of 4-bit values (0..15) with the baseline at row `base`."""
    im = Image.new('L', (cell * 4, cell * 4), 0)  # 4x supersample for fractional sizes
    big = ImageFont.truetype(HIRAGINO, size=size * 4, index=face)
    ImageDraw.Draw(im).text((dx * 4, base * 4), ch, font=big, fill=255, anchor='ls')
    im = im.resize((cell, cell), Image.BOX)
    return im.point(lambda v: round(v * 15 / 255))
