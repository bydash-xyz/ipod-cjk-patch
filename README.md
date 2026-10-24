# iPod CJK Patch

**Clean Chinese, Japanese and Korean text for the iPod Video 5G/5.5G on stock firmware 1.3.**

**English** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

Makes Chinese, Japanese and Korean text render cleanly on an **iPod Video 5G/5.5G** running
Apple's stock firmware **1.3** (`iPod_25.1.3.ipsw`). It isn't Rockbox: the Apple firmware keeps
working as before and only its fonts change. Your music stays on the iPod.

On stock firmware, CJK lyrics mix four bitmap font families. Characters jump up and down by
1–2px, styles change mid-line, and some characters (啰, 嘢, 哋, …) are blank. Latin letters and
symbols in the same lines come from yet another font, a bold antialiased one. Menu text
(song, artist and album names) is missing many Simplified Chinese characters (泷, 犸, …).

![Stock vs patched: menu and lyric text rendered from each firmware's own fonts](docs/before-after.png)

<sub>Rendered from each firmware's own font data by `tools/render_preview.py` (3× scale). On
stock, each character takes Podium Sans 16 if it has it, else the first 12px font in the firmware's
font registry that has it. The device's real lookup order for CJK differs slightly, but the mix of
fonts is the same.</sub>

> **Use at your own risk.** This writes to your iPod's firmware partition. The flash script
> checks everything it can and makes a backup first, and a restore in Finder/iTunes always
> recovers the iPod, but that erases its music.

## What it changes

- **Lyrics (12px bitmap fonts compiled into the OS image).** Every CJK character (19.5k: Han,
  kana, Hangul, CJK punctuation, fullwidth forms) is redrawn from
  [Fusion Pixel 12px](https://github.com/TakWolf/fusion-pixel-font) (OFL), and all of them share
  one cell and one baseline. Each character has exactly one source font, so the firmware's
  font-fallback order no longer matters. Simplified characters use the zh_hans glyphs, Traditional
  ones zh_hant, Japanese-only kanji and kana ja, and Hangul ko. Characters missing from stock are
  added, and Kangxi radical lookalikes (⼀ ⼩ ⾸ ⻋) alias to the normal characters.
- **Latin and symbols in lyrics (Podium Sans 16, also in the OS image).** Lyrics draw everything
  that isn't CJK from this bold, antialiased font, so English words, brackets and quotes looked
  heavier than the CJK beside them. Its glyphs are redrawn from Fusion Pixel 12px proportional,
  on the same baseline as the CJK. Symbols that stock only has in the CJK fonts (♪ ★ ① → ※, box
  drawing) move into it too, so each has one style. Characters Fusion Pixel lacks (Vietnamese
  and other rare accented letters, Apple's private icons) keep their stock glyphs. Podium Sans 16
  may also be used outside the lyrics screen; any text there changes the same way.
- **Menus / Now Playing (`CJK.ttf`, 18px 4-bit, in the resource volume).** 630 glyphs are
  added: all of GB2312 that was missing, plus characters from `charsets/menu.txt`. They are
  rasterized from Hiragino Sans GB W6 to match the existing Hiragino glyphs.

## Requirements

- iPod Video 5G or 5.5G on firmware 1.3 (tested on a 5.5G), **Mac-formatted**
  (Windows/FAT32-formatted iPods use a different partition layout and aren't supported by the
  flash script)
- macOS: the menu font uses the system's Hiragino Sans GB, and flashing uses `diskutil`
- [uv](https://docs.astral.sh/uv/) (or Python ≥ 3.11 with `fonttools`, `pillow`, `mutagen`)
- An internet connection for the first build: the stock `iPod_25.1.3.ipsw` is downloaded from
  Apple's server (Apple's firmware is copyrighted, so it isn't in this repository)

## Build

```bash
uv run python -I tools/build.py
```

This downloads `iPod_25.1.3.ipsw` from Apple into `build/` and checks it against the known SHA1
(`0f2dd984c5d56475bdf3c14b4bc7541b799f2c85`) and SHA256. Apple serves the file only over plain
HTTP, so the hashes are what make it safe. If you already have the IPSW, pass
`--ipsw path/to/iPod_25.1.3.ipsw` to skip the download.

The lyric glyphs come from the Fusion Pixel 12px BDF release (v2026.09.25) on GitHub. The build
also downloads that file and the proportional one (for Latin and symbols), checks them against
pinned SHA256s, and caches them in `build/`.

The build writes `build/Firmware-25.6.3-cjk`, the stock base `build/stock/Firmware-25.6.3`, and
`build/before-after.png`. It's deterministic, and the script tells you whether your output
matches the released build (SHA256
`bf83fc2e3c38ba82da93f4f058783bfe9ef38899f6eb6dbf93fae567239b97e8`).

## Flash (keeps music)

1. Connect the iPod and enable disk use (or put it in disk mode: hold Menu+Select to reset,
   then Select+Play).
2. Find its disk number with `diskutil list`. The iPod has an `Apple_MDFW` partition at
   `diskNs2`.
3. Run:

```bash
sudo zsh tools/backup_and_flash.sh /dev/diskN
```

The script backs up the partition map and the firmware partition to `backups/`. It refuses to
write unless the iPod's current firmware matches `build/stock/Firmware-25.6.3` byte for byte. It
does a dry run, writes only the sectors that change, verifies them by reading back, and ejects
the iPod. Then reboot the iPod (hold Menu+Select).

To flash on top of an earlier build instead of stock, pass the image the iPod holds now and the
new one: `backup_and_flash.sh /dev/diskN <current image> <new image>`.

## Roll back

Write back the firmware partition backup the script made (put the iPod in disk mode if it won't
boot):

```bash
sudo dd if=backups/ipod-s2-YYYYMMDD-HHMMSS.img of=/dev/rdiskNs2 bs=1m
```

A restore in Finder/iTunes also works, but it erases the music.

## Adding characters

Append characters to `charsets/lyrics_extra.txt` (lyrics) or `charsets/menu.txt` (menus) and
rebuild. In `lyrics_extra.txt`, symbols that aren't CJK (such as ♫) are added to Podium Sans 16. To find characters your library uses that a firmware can't draw well:

```bash
uv run python -I tools/scan_library.py ~/Music/your-library build/Firmware-25.6.3-cjk report.json
```

It reports characters missing from every 12px font, characters in more than one font (the cause
of the jumping baseline on stock), and title/artist/album characters missing from `CJK.ttf`.

`tools/make_test_track.py` tags a short silent `.m4a` with a title, artist, album and lyrics
that exercise every case. Add the track to your library and check it on the iPod.

## Tools

| File | Purpose |
|---|---|
| `tools/build.py` | One-step build: download + verify the IPSW, build, render preview |
| `tools/build_unified.py` | Rebuilds the 12px CJK bitmap fonts in the `osos` image |
| `tools/build_latin.py` | Redraws Podium Sans 16 (lyrics' Latin and symbols) from Fusion Pixel |
| `tools/extend_cjk_ttf.py` | Appends glyphs to `CJK.ttf`'s 18px EBDT strike |
| `tools/build_rsrc.py` | Replaces a file in the `rsrc` FAT volume and fixes its checksum |
| `tools/install_firmware.py` | Patches the device's firmware partition in place (stdlib only) |
| `tools/backup_and_flash.sh` | Backup + safety checks + `install_firmware.py` |
| `tools/scan_library.py` | Reports library characters a firmware can't draw well |
| `tools/render_preview.py` | Renders text from two firmwares' fonts side by side (`docs/before-after.png`) |
| `tools/pixofont.py` | Parser/writer for the firmware's bitmap fonts; `pixofont.py <fw>` lists them |
| `tools/fat16.py`, `ipodfw.py`, `bdf.py`, `hiragino_raster.py` | Supporting readers/writers |

## Firmware notes (things that bit)

- Each image's data starts at directory `devOffset + 0x800` in the IPSW file (`+ entryOffset` for
  `rsrc`), but at `devOffset + 0x200` on the device. Checksums are 32-bit byte sums of the image.
- The `rsrc` volume is FAT12, despite its "FAT16" label.
- **A fixed-width 12px font's glyph strip must stay ≤ 32767px** (the glyph x is a signed 16-bit
  value). Past the limit, every glyph renders blank. Apple's largest strip is 31836px, and
  `build_unified.py` enforces that, which allows about 2,400 glyphs per font.
- Don't rely on the firmware's font-fallback order. It doesn't follow the font registry order.
  Give each character exactly one source font.
- Lyrics are drawn with Podium Sans 16 first; only characters it lacks fall back to the 12px
  fonts. Glyphs from different fonts on one line are aligned by the bottom of their cells, not by
  their declared ascent (measured from a photo: Podium Sans 16's 13px parentheses end on the same
  row as the CJK).
- The bitmap font format follows iPodWizard's `Font.h`.

## Help wanted: more iPods and firmware versions

So far this has only been tested on one **iPod Video 5.5G with firmware 1.3, Mac-formatted**.
If you have other hardware, you can help make it work for more people:

- **Test reports:** a 5G (30/60GB) on 1.3, or a Windows-formatted iPod. Tell us what works and
  what doesn't, ideally with photos.
- **Other firmware versions:** 1.2.x and earlier 5G firmware probably lay things out differently.
- **Other models:** nano and classic models may use other firmware formats. Even an analysis of how
  their fonts are stored is a useful start.

[CONTRIBUTING.md](CONTRIBUTING.md#porting-to-another-ipod-or-firmware) lists exactly which parts
are tied to this model and version, and there's an issue template for porting reports.

## Contributing

Issues and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Coding agents
should also read [AGENTS.md](AGENTS.md).

## Acknowledgements

- [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) by TakWolf (OFL 1.1) provides
  the lyric glyphs. It builds on [Ark Pixel](https://github.com/TakWolf/ark-pixel-font),
  [Cubic 11](https://github.com/ACh-K/Cubic-11) and [Galmuri](https://github.com/quiple/galmuri).
- [iPodWizard](https://sourceforge.net/projects/ipodwizard/): its `Font.h` documents the
  firmware's bitmap font format, which `tools/pixofont.py` follows.
- Menu glyphs are rasterized on your Mac from the system font Hiragino Sans GB. No Hiragino data
  is in this repository.
- Built with [fontTools](https://github.com/fonttools/fonttools),
  [Pillow](https://python-pillow.org/) and [mutagen](https://github.com/quodlibet/mutagen).

iPod is a trademark of Apple Inc. This project is not affiliated with or endorsed by Apple.

## License

The code is MIT licensed (see `LICENSE`). Fusion Pixel is under the SIL Open Font License 1.1;
its license texts and provenance are in `third_party/fusion-pixel/`. The repository contains no
font files, no Apple firmware and no Apple fonts. The build downloads Apple's IPSW and the
Fusion Pixel release and patches the firmware locally, and `build/` is git-ignored. Don't publish
built firmware images.
