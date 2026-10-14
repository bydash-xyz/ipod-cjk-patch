# Fusion Pixel Font 12px

The lyric glyphs come from [TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font),
release 2026.09.25, asset `fusion-pixel-font-12px-monospaced-bdf-v2026.09.25.zip`
(SHA256 `d75f5262f108757edb0f47ee8e3d2dfdfbecfd94558faf5ffb0c06dc5866fb3b`).

The font files aren't stored in this repository. `tools/build.py` downloads the zip, checks the
SHA256, and extracts the zh_hans, zh_hant, ja and ko BDFs (unmodified) into
`build/fusion-pixel/`.

Fusion Pixel is licensed under the SIL Open Font License 1.1 (`OFL.txt`, copied from the
release). It includes glyphs from Ark Pixel, Cubic 11 and Galmuri, whose licenses are in
`LICENSES/`. The patched firmware contains glyphs derived from these fonts.

To move to a newer release, update `FUSION_VERSION` and `FUSION_SHA256` in `tools/build.py`. The
firmware hash will change, so also follow the "changed on purpose" steps in CONTRIBUTING.md.
