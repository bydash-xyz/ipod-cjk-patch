# Fusion Pixel Font 12px

The lyric glyphs come from [TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font),
release 2026.09.25, assets:

- `fusion-pixel-font-12px-monospaced-bdf-v2026.09.25.zip`
  (SHA256 `d75f5262f108757edb0f47ee8e3d2dfdfbecfd94558faf5ffb0c06dc5866fb3b`): CJK
- `fusion-pixel-font-12px-proportional-bdf-v2026.09.25.zip`
  (SHA256 `7cae5ea83b46086f146002d194d46bbba70ec7264ac3a309219f5ad491626cef`): Latin and symbols

The font files aren't stored in this repository. `tools/build.py` downloads the zips, checks the
SHA256s, and extracts the monospaced zh_hans, zh_hant, ja and ko BDFs and the proportional latin
and zh_hans BDFs (unmodified) into `build/fusion-pixel/`.

Fusion Pixel is licensed under the SIL Open Font License 1.1 (`OFL.txt`, copied from the
release). It includes glyphs from Ark Pixel, Cubic 11 and Galmuri, whose licenses are in
`LICENSES/`. The patched firmware contains glyphs derived from these fonts.

To move to a newer release, update `FUSION_VERSION` and the hashes in `FUSION_ASSETS` in
`tools/build.py`. The
firmware hash will change, so also follow the "changed on purpose" steps in CONTRIBUTING.md.
