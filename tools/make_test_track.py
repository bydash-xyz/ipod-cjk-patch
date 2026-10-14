"""Tag a short silent track with CJK title/artist/album/lyrics that exercise every font path.

usage: make_test_track.py <file.m4a>
Make the silent track first, e.g.:
    ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 20 -c:a aac ipod-cjk-test.m4a
Title/artist/album test the menus (CJK.ttf); lyrics test the 12px bitmap fonts. On the patched
firmware every CJK char in the lyrics should sit on one baseline in one style.
"""
import sys

from mutagen.mp4 import MP4

TITLE = '汪苏泷 嗨啰 說話 夜に駆ける 사랑'      # menu path: CJK.ttf (泷 啰 were missing)
ARTIST = '达达乐队 & 汪苏泷'                    # menu path: the photo's broken entry
ALBUM = 'iPod CJK 字体测试 犸嫫恓'              # menu path: 犸 嫫 恓 were missing from CJK.ttf
LYRICS = '\n'.join([
    '[简体] 再也不愿意 让你偷偷的溜走',          # stock: 你偷偷 drop 1px
    '[简体] 问姑娘何时能回首',                  # stock: 问/时 sit 1px high
    '[繁體] 妳說過會一直愛我嗎',                # Traditional forms (zh_hant)
    '[繁體] 這個時候 讓我們離開',                # stock: mixes TC and SC fonts
    '[日本語] 僕達はなんとなく幸せになるんだ',    # kana + kanji on one baseline
    '[日本語] 夕暮れが僕のドアをノックする頃に',  # katakana + JIS-only kanji (頃)
    '[日本語] 気持ち 様子 実は',                # Japanese-only kanji forms
    '[新增] (合)嗨啊啰哩嗨啊啰哩嗨',            # 啰 added from Fusion Pixel
    '[新增] 嘢 哋 嘅 瞓 嫲 阇 坔',               # Cantonese / rare chars added
    '[部首] 花⼀样的年纪 ⼩ ⾸ ⻋',              # radical codepoints aliased to 一 小 首 车
    '[한국어] 사랑해요 我爱你',                  # Hangul next to Han
    '[混合] Yasushi Nishino（西野靖）：吉他',      # Latin (Podium Sans) + fullwidth punctuation
])


def main(path):
    f = MP4(path)
    f['\xa9nam'] = TITLE
    f['\xa9ART'] = ARTIST
    f['aART'] = ARTIST
    f['\xa9alb'] = ALBUM
    f['\xa9lyr'] = LYRICS
    f['\xa9gen'] = 'Test'
    f.save()
    print(f'tagged {path}\n  title:  {TITLE}\n  artist: {ARTIST}\n  album:  {ALBUM}\n'
          f'  lyrics: {len(LYRICS.splitlines())} lines')


if __name__ == '__main__':
    main(sys.argv[1])
