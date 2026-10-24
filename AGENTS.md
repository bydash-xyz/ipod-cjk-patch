# AGENTS.md

Guidance for coding agents working on iPod CJK Patch (`ipod-cjk-patch`). For what the project
does and how users build and flash it, read [README.md](README.md) first; this file covers what
an agent needs on top of that.

## Hard rules

- **Never flash a device on your own.** `tools/backup_and_flash.sh` and
  `tools/install_firmware.py --write` write to an iPod's firmware partition and need `sudo`. Only
  run them when the user asks in so many words, with the disk they named. Dry runs
  (`install_firmware.py` without `--write`) against a file copy of a partition are fine.
- **Never commit Apple material.** No `.ipsw`, firmware images (`Firmware-*`), partition backups
  (`*.img`), extracted `rsrc` files, or fonts derived from Apple fonts (`build/CJK.ttf`). They are
  git-ignored; keep it that way. `docs/before-after.png` is the one exception: a small rendering
  for the README.
- **Issues and PRs need a human-written summary.** CONTRIBUTING.md requires every issue and
  pull request to start with at least one sentence written by a person. When you draft one, leave
  the "Summary (written by you)" field for the user and ask them for it. Never write it yourself,
  and don't paraphrase their words into it.
- **Don't break determinism.** `tools/build.py` checks its output against `EXPECTED_SHA256`. If a
  change is meant to alter the firmware, update that hash, the hash in all four READMEs, and
  `docs/before-after.png` in the same change. If it isn't meant to, the hash must still match.

## Commands

```bash
uv run python -I tools/build.py                 # download + verify IPSW, build, render preview
uv run python -I tools/build.py --ipsw FILE     # same, from a local IPSW
uvx ruff check --select E,F,W --line-length 120 tools/
uv run python -I tools/pixofont.py build/Firmware-25.6.3-cjk     # list the 12px fonts
uv run python -I tools/scan_library.py DIR build/Firmware-25.6.3-cjk report.json
```

Always run Python with `-I`. The tools add their own directory to `sys.path` for that reason.
The menu font build needs macOS (it rasterizes from `/System/Library/Fonts/Hiragino Sans GB.ttc`).

## How to verify a change

There are no unit tests; the firmware is the test. After changing anything under `tools/` or
`charsets/`, or the pinned downloads in `tools/build.py`:

1. `tools/build.py` succeeds, and the hash either still matches or changed on purpose.
2. Look at `build/before-after.png`: the patched lyric lines sit on the red rule with no 1px
   jumps, and no characters are blank.
3. `tools/scan_library.py` on a folder with a track tagged by `tools/make_test_track.py` reports
   0 MISSING, 0 MULTIPLE_FONTS and 0 MENU_MISSING_FROM_CJK_TTF for the patched firmware.
4. ruff passes.

Only the user can confirm on real hardware. Say so when you report, rather than claiming it works on
a device.

## Invariants the firmware enforces

These are learned the hard way (see "Firmware notes" in the README); code must keep them:

- A fixed-width 12px font's glyph strip must stay ≤ 31836px (the firmware uses a signed 16-bit x;
  past 32767px every later glyph renders blank). `build_unified.py` asserts it.
- Every CJK character must live in exactly one 12px font. The firmware's fallback order is not
  the registry order, so two sources means unpredictable style and baseline.
- Lyrics draw Latin and symbols from Podium Sans 16 first, and the firmware aligns mixed fonts by
  the bottom of their glyph cells. `build_latin.py` keeps that font's header and places Fusion
  glyphs for that alignment; don't move it to another font or cell height without a device photo.
- Rebuilt fonts must fit back into the space the original CJK fonts occupied in `osos`, and the
  font registry entries are repointed, not added.
- After changing an image, recompute its checksum (`ipodfw.fix_checksum`).
- `install_firmware.py` must stay standard-library only: it runs as root under the system
  `python3`.

## Layout

`tools/` holds all code (see the Tools table in the README). `charsets/` holds the extra
characters for lyrics and menus. The source glyphs (Fusion Pixel, OFL) are downloaded by
`tools/build.py` from a pinned GitHub release into `build/fusion-pixel/`. `third_party/fusion-pixel/`
holds only their licenses and provenance. Don't commit font files. `docs/` holds the README image. `build/` and `backups/` are local-only output.

## Style

Match the existing code: small single-purpose scripts, a module docstring with usage, plain
`sys.argv` handling (argparse only where options are optional), comments that explain *why* (usually a
firmware quirk). Keep the four READMEs in sync when you change user-facing behaviour.
