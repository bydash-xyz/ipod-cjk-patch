"""Build a 1.3 firmware where ALL 12px CJK glyphs in lyrics come from one font family.

Background: the firmware draws lyric text with 12px bitmap fonts AppleGothic (KR),
AppleLiGothicMedium (TC), Hei (SC) and Osaka (JP), choosing per character among those that
contain it. The four families position glyphs differently and the selection order is not fully
predictable, so mixed lines show 1-2px vertical jumps. Here every CJK character (Han, kana,
Hangul, CJK punctuation, fullwidth forms) is redrawn from Fusion Pixel 12px (OFL) and placed in
the Hei font entries -- all with Hei's cell/metrics -- and removed from the other three
families. Whatever order the firmware checks fonts in, a CJK char now has exactly one source.

Fusion variant per char: Simplified (GB2312) -> zh_hans, else Traditional (Big5) -> zh_hant,
kana / other JIS kanji -> ja, Hangul -> ko. Compatibility forms (e.g. Kangxi radical U+2F00)
alias the normal glyph. All rebuilt fonts are repacked into the space the original CJK fonts
occupied and the font registry is repointed.

usage: build_unified.py <stock Firmware-25.6.3> <output> <fusion bdf dir> [extra chars file]
"""
import struct
import sys
import unicodedata

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from bdf import load, to_image  # noqa: E402
from pixofont import scan, subset  # noqa: E402

OSOS_DIR, OSOS_DATA = 0x4200, 0x5000
REGISTRY = (0x6a6480, 0x6a6660)
FAMILIES = ('AppleGothic', 'AppleLiGothicMedium', 'Hei', 'Osaka')
FUSION_BASELINE = 11   # Hei cell row that Fusion's baseline maps to (Han ink -> rows 2..12)
RADICAL_ALIASES = {0x2ECB: 0x8F66}  # ⻋ -> 车 (not covered by NFKC)
MAX_GLYPHS = 2400        # per font: 2400 x 12px = 28800px strip
STRIP_LIMIT = 31836      # largest strip in Apple's stock fonts; firmware breaks past 32767
# Chars Fusion lacks are copied from the old fonts into the unified cell. Rows to move a glyph so
# its family's Han ink box (measured: LiGothic/Hei end 1px below their baseline, AppleGothic/Osaka
# on it) lands where Fusion's does (rows 2..12 of the 12x15 Hei cell).
OLD_SOURCES = ('AppleLiGothicMedium', 'Osaka', 'AppleGothic', 'Hei')
FAMILY_HAN_OFFSET = {'AppleLiGothicMedium': 0, 'Hei': 0, 'AppleGothic': 1, 'Osaka': 1}


def is_target(cp):
    return (0x2E80 <= cp <= 0x2FDF or 0x3000 <= cp <= 0x30FF or 0x3100 <= cp <= 0x318F
            or 0x31A0 <= cp <= 0x31BF
            or 0x31F0 <= cp <= 0x31FF or 0x3400 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF
            or 0xF900 <= cp <= 0xFAFF or 0xFF01 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6)


def charset(codec, lead, trail):
    out = set()
    for b1 in lead:
        for b2 in trail:
            try:
                s = bytes([b1, b2]).decode(codec)
            except UnicodeDecodeError:
                continue
            if len(s) == 1:
                out.add(ord(s))
    return out


def main(src, dst, fusion_dir, extra_chars=None):
    fw = bytearray(open(src, 'rb').read())
    _t, ident, _z, dev_off, length, _a, _e, chk = struct.unpack_from('<4s4s6I', fw, OSOS_DIR)
    assert ident == b'soso' and dev_off + 0x800 == OSOS_DATA
    assert sum(fw[OSOS_DATA:OSOS_DATA + length]) & 0xFFFFFFFF == chk, 'stock osos checksum mismatch'
    osos_end = OSOS_DATA + length
    fonts = scan(bytes(fw), OSOS_DATA, osos_end)
    ranged = [f for f in fonts if f.size == 12 and '_' in f.name and f.name.split('_')[0] in FAMILIES]
    hei = {f.name: f for f in ranged if f.name.startswith('Hei_')}

    gb = charset('gb2312', range(0xA1, 0xF8), range(0xA1, 0xFF))
    big5 = charset('big5', range(0xA1, 0xFA), list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF)))
    jis = charset('euc_jp', range(0xA1, 0xF5), range(0xA1, 0xFF))
    ksc = charset('euc_kr', range(0xA1, 0xFE), range(0xA1, 0xFF))
    fusion = {v: load(f'{fusion_dir}/fusion-pixel-12px-monospaced-{v}.bdf')[0]
              for v in ('zh_hans', 'zh_hant', 'ja', 'ko')}

    def variant(cp):
        if 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:
            return 'ja'
        if 0xAC00 <= cp <= 0xD7AF or 0x3130 <= cp <= 0x318F:
            return 'ko'
        if cp in gb or 0x3000 <= cp <= 0x303F or cp >= 0xFF00:
            return 'zh_hans'
        if cp in big5:
            return 'zh_hant'
        if cp in jis:
            return 'ja'
        return 'zh_hans'

    def fusion_glyph(cp):
        for v in (variant(cp), 'zh_hans', 'zh_hant', 'ja', 'ko'):
            g = fusion[v].get(cp)
            if g and g[4] == 12:  # full-width only; fixed 12px cells
                return g
        return None

    covered = {c for f in ranged for c in f.codepoints()}
    wanted = {c for c in covered | gb | big5 | jis | ksc if is_target(c)}
    if extra_chars:
        wanted |= {ord(c) for c in open(extra_chars, encoding='utf-8').read() if is_target(ord(c))}

    # decide each wanted char: alias / Fusion image / leave in old font
    from PIL import Image
    images, aliases, unavailable = {}, {}, []
    for cp in sorted(wanted):
        norm = RADICAL_ALIASES.get(cp) or (ord(unicodedata.normalize('NFKC', chr(cp)))
                                           if len(unicodedata.normalize('NFKC', chr(cp))) == 1 else cp)
        if norm != cp and fusion_glyph(norm):
            aliases[cp] = norm
            continue
        g = fusion_glyph(cp)
        if g is None:
            unavailable.append(cp)
            continue
        im, ox, oy, _dw = to_image(g)
        y = FUSION_BASELINE - (oy + im.height)
        assert ox >= 0 and ox + im.width <= 12 and y >= 0 and y + im.height <= 15, f'U+{cp:04X} does not fit'
        cell = Image.new('L', (12, 15), 0)
        cell.paste(im, (ox, y))
        images[cp] = cell
    for cp, tgt in aliases.items():  # alias targets must be drawn too
        if tgt not in images:
            im, ox, oy, _dw = to_image(fusion_glyph(tgt))
            cell = Image.new('L', (12, 15), 0)
            cell.paste(im, (ox, FUSION_BASELINE - (oy + im.height)))
            images[tgt] = cell
    copied = 0
    for cp in unavailable:
        src = next((f for fam in OLD_SOURCES for f in ranged
                    if f.name.split('_')[0] == fam and f.char_index(cp) is not None), None)
        if src is None:
            continue
        g = src.glyph(cp)[0]
        fam = src.name.split('_')[0]
        dy = 12 - (src.height - src.descent) + FAMILY_HAN_OFFSET[fam]
        cell = Image.new('L', (12, 15), 0)
        bb = g.getbbox()
        if bb:
            ink = g.crop(bb)
            assert 0 <= bb[1] + dy and bb[3] + dy <= 15 and bb[2] <= 12, f'U+{cp:04X} from {src.name}'
            cell.paste(ink, (bb[0], bb[1] + dy))
        images[cp] = cell
        copied += 1
    unified = set(images) | set(aliases)
    print(f'unified chars: {len(images)} glyphs ({copied} copied from old fonts) + {len(aliases)} aliases')

    # Split unified glyphs into chunks. The firmware addresses a fixed-width font's glyph strip
    # with a signed 16-bit pixel x, so a strip must stay < 32768 px (Apple's largest: 31836).
    # Chunks go to the Hei entries first, then to entries that would otherwise be left with no
    # CJK at all (their CJK moved here); those get Hei's cell/metrics so they render identically.
    template = hei['Hei_5000_5FFF']
    # overflow hosts: AppleLiGothicMedium entries first (that family measured on-device exactly
    # aligned with Hei; AppleGothic measured 1px high), then any other emptied entry
    emptied = [f.name for f in ranged if f.name not in hei
               and not any(cp not in unified for cp in f.codepoints())]
    hosts = list(hei) + sorted(emptied, key=lambda n: not n.startswith('AppleLiGothicMedium'))
    order = sorted(images)
    n_chunks = -(-len(order) // MAX_GLYPHS)
    size = -(-len(order) // n_chunks)
    chunks = [order[i:i + size] for i in range(0, len(order), size)]
    assert len(chunks) <= len(hosts), f'need {len(chunks)} host fonts, have {len(hosts)}'
    host_of = {cp: hosts[i] for i, chunk in enumerate(chunks) for cp in chunk}
    extras = {n: {} for n in hosts}
    for cp in order:
        extras[host_of[cp]][cp] = ('image', images[cp])
    for cp, tgt in aliases.items():
        extras[host_of[tgt]][cp] = ('alias', tgt)  # alias must live with its target glyph

    by_name = {f.name: f for f in ranged}
    built = []
    for f in ranged:
        if f.name in hei:
            blob, h2 = subset(f, lambda cp: cp not in unified, None, extras[f.name])
        elif f.name in extras and extras[f.name]:
            # host font: Hei template cell + metrics, keep this entry's name
            blob, h2 = subset(template, lambda cp: False, None, extras[f.name])
            blob = bytearray(blob)
            blob[h2 + 2:h2 + 68] = by_name[f.name].name.encode('latin1').ljust(66, b'\0')
            blob = bytes(blob)
        else:
            blob, h2 = subset(f, lambda cp: cp not in unified)
        built.append((f, blob, h2))
    for f, blob, _h2 in built:  # hard limit check on the rebuilt strips
        g = scan(blob, 0, len(blob))[0]
        assert g.row_pixels <= STRIP_LIMIT, f'{f.name}: strip {g.row_pixels}px exceeds {STRIP_LIMIT}'
    print('fonts holding unified glyphs:', ', '.join(f'{n}({len(extras[n])})' for n in hosts if extras[n]))

    # repack every rebuilt font into the contiguous regions the ranged fonts occupied
    spans = sorted((f.off, f.end) for f in ranged)
    regions = []
    for a, b in spans:
        if regions and regions[-1][1] == a:
            regions[-1][1] = b
        else:
            regions.append([a, b])
    for a, b in regions:
        fw[a:b] = bytes(b - a)
    cursor = [[a, b] for a, b in regions]
    placement = {}
    for f, blob, h2 in sorted(built, key=lambda t: -len(t[1])):
        r = next((r for r in cursor if r[1] - r[0] >= len(blob)), None)
        assert r, f'out of space for {f.name} ({len(blob)} bytes)'
        placement[f.name] = r[0]
        fw[r[0]:r[0] + len(blob)] = blob
        r[0] = (r[0] + len(blob) + 3) // 4 * 4
    for f, blob, h2 in built:
        o = [o for o in range(*REGISTRY, 4) if struct.unpack_from('<I', fw, o)[0] == f.off - OSOS_DATA
             and struct.unpack_from('<I', fw, o + 4)[0] == f.h2_off - OSOS_DATA]
        assert len(o) == 1, f.name
        at = placement[f.name]
        struct.pack_into('<II', fw, o[0], at - OSOS_DATA, at + h2 - OSOS_DATA)
        print(f'{f.name:32s} {f.nchars:5d} -> {struct.unpack_from("<H", blob, 10)[0]:5d} chars '
              f'{len(blob):7d} bytes @ {at:#x}')
    used = sum(len(b) for _f, b, _h in built)
    total = sum(b - a for a, b in regions)
    print(f'font space used {used / 1024:.0f} KB of {total / 1024:.0f} KB')

    new_chk = sum(fw[OSOS_DATA:osos_end]) & 0xFFFFFFFF
    struct.pack_into('<I', fw, OSOS_DIR + 28, new_chk)
    open(dst, 'wb').write(fw)
    print(f'osos checksum {chk:#010x} -> {new_chk:#010x}; wrote {dst}')


if __name__ == '__main__':
    if not 4 <= len(sys.argv) <= 5:
        sys.exit(__doc__)
    main(*sys.argv[1:5])
