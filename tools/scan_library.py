"""Scan music tags (title/artist/album/album artist/lyrics) for CJK characters a firmware
can't draw well:

  MISSING                    in no 12px bitmap font (lyrics show nothing for it)
  MULTIPLE_FONTS             in more than one 12px font, so its style/baseline may not match
                             its neighbours (common on stock firmware; should be empty when patched)
  MENU_MISSING_FROM_CJK_TTF  used in a title/artist/album but missing from the firmware's
                             CJK.ttf (menus fall back to the small 12px bitmap)

Read-only. usage: scan_library.py <music dir> <firmware file> [report.json]
"""
import collections
import json
import os
import sys

import mutagen

sys.path.insert(0, os.path.dirname(__file__))
import ipodfw  # noqa: E402
from build_rsrc import read_file  # noqa: E402
from pixofont import scan  # noqa: E402

AUDIO = ('.mp3', '.m4a', '.m4p', '.aac', '.m4b', '.wav', '.aif', '.aiff', '.flac')
FIELDS = {  # tag keys per format -> logical field
    'TIT2': 'title', 'TPE1': 'artist', 'TALB': 'album', 'TPE2': 'albumartist',
    '\xa9nam': 'title', '\xa9ART': 'artist', '\xa9alb': 'album', 'aART': 'albumartist',
    '\xa9lyr': 'lyrics', 'title': 'title', 'artist': 'artist', 'album': 'album',
    'albumartist': 'albumartist', 'lyrics': 'lyrics', 'unsyncedlyrics': 'lyrics',
}


def is_cjk(cp):
    return (0x2E80 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF or 0xFF00 <= cp <= 0xFFEF
            or 0xAC00 <= cp <= 0xD7AF or 0x20000 <= cp <= 0x3FFFF)


def tag_texts(path):
    f = mutagen.File(path)
    if f is None or f.tags is None:
        return
    for key, val in f.tags.items():
        if key.startswith('USLT'):
            yield 'lyrics', str(val)
            continue
        field = FIELDS.get(key.split(':')[0]) or FIELDS.get(key.lower())
        if not field:
            continue
        vals = val if isinstance(val, list) else getattr(val, 'text', [val])
        for v in vals:
            yield field, str(v)


def main(music_dir, fw_path, out='library_report.json'):
    import io

    from fontTools.ttLib import TTFont
    fw = open(fw_path, 'rb').read()
    ttf_cmap = TTFont(io.BytesIO(read_file(fw, '/Resources/Fonts/CJK.ttf'))).getBestCmap()
    menu = collections.Counter()
    menu_ex = {}
    fonts = [f for f in scan(fw, *ipodfw.data_range(fw, 'osos')) if f.size == 12]

    def fonts_for(cp):
        return [f.name for f in fonts if f.char_index(cp) is not None]

    counts = collections.Counter()      # char -> occurrences
    where = collections.defaultdict(set)  # char -> fields it appears in
    examples = {}
    nfiles = errors = 0
    paths = [os.path.join(root, name) for root, _dirs, files in os.walk(music_dir)
             for name in files if name.lower().endswith(AUDIO)]

    def read_tags(path):  # I/O bound (network share): run many in parallel
        try:
            return list(tag_texts(path))
        except Exception:  # unreadable/corrupt tags
            return None

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(16) as pool:
        results = pool.map(read_tags, paths)
        for tags in results:
            nfiles += 1
            if tags is None:
                errors += 1
                continue
            for field, text in tags:
                for ch in text:
                    if is_cjk(ord(ch)):
                        if field != 'lyrics' and ord(ch) not in ttf_cmap and not 0xAC00 <= ord(ch) <= 0xD7AF:
                            menu[ch] += 1
                            menu_ex.setdefault(ch, text.strip()[:40])
                        counts[ch] += 1
                        where[ch].add(field)
                        examples.setdefault(ch, text.strip().splitlines()[0][:40] if field != 'lyrics'
                                            else next((ln for ln in text.splitlines() if ch in ln), '')[:40])
            if nfiles % 1000 == 0:
                print(f'  {nfiles} files...', flush=True)

    report = {'MISSING': [], 'MULTIPLE_FONTS': []}
    for ch, n in counts.most_common():
        names = fonts_for(ord(ch))
        if len(names) == 1:
            continue
        item = {'char': ch, 'cp': f'U+{ord(ch):04X}', 'count': n,
                'fields': sorted(where[ch]), 'example': examples[ch]}
        if names:
            item['fonts'] = names
        report['MULTIPLE_FONTS' if names else 'MISSING'].append(item)
    report['MENU_MISSING_FROM_CJK_TTF'] = [{'char': ch, 'cp': f'U+{ord(ch):04X}', 'count': n,
                                            'example': menu_ex[ch]} for ch, n in menu.most_common()]
    json.dump(report, open(out, 'w'), ensure_ascii=False, indent=1)
    print(f'\nscanned {nfiles} files ({errors} unreadable), {len(counts)} distinct CJK chars')
    for fam, items in sorted(report.items(), key=lambda kv: -sum(i['count'] for i in kv[1])):
        total = sum(i['count'] for i in items)
        print(f'\n{fam}: {len(items)} distinct chars, {total} occurrences')
        print('  ' + ' '.join(f"{i['char']}×{i['count']}" for i in items[:60]))
    print(f'\nfull report: {out}')


if __name__ == '__main__':
    main(*sys.argv[1:])
