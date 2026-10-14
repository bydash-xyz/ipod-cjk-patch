"""Build the patched firmware from Apple's stock iPod_25.1.3.ipsw in one step.

usage: uv run python -I tools/build.py [--ipsw iPod_25.1.3.ipsw] [--out build]

Without --ipsw, the IPSW is downloaded from Apple. The Fusion Pixel 12px BDFs are downloaded
from the font's GitHub release. Both downloads happen once and are kept in the build dir, and
each must match a pinned hash before anything is built. Writes to the build dir:
  iPod_25.1.3.ipsw          downloaded stock IPSW (if not given)
  fusion-pixel/             the four 12px BDFs used for lyrics (zh_hans, zh_hant, ja, ko)
  stock/Firmware-25.6.3     stock firmware from the IPSW (the base for flashing)
  CJK.ttf                   extended menu font
  Firmware-25.6.3-cjk       the patched firmware
  before-after.png          stock vs patched rendering (tools/render_preview.py)
The build is deterministic; the result is checked against EXPECTED_SHA256.
"""
import argparse
import hashlib
import os
import sys
import urllib.request
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build_rsrc  # noqa: E402
import build_unified  # noqa: E402
import extend_cjk_ttf  # noqa: E402
import render_preview  # noqa: E402

# From Apple's iTunes version catalog. Apple only serves it over plain HTTP; the hashes below
# are what make the download trustworthy.
IPSW_URL = ('http://appldnld.apple.com.edgesuite.net/content.info.apple.com/iPod/SBML/osx/'
            'bundles/061-2967.20080313.Cnvkg/iPod_25.1.3.ipsw')
IPSW_SHA1 = '0f2dd984c5d56475bdf3c14b4bc7541b799f2c85'
IPSW_SHA256 = '840b2480ad5b692c098cb772c3d2bf8f58bf37557788782b596ac01c27ecdc32'
# Fusion Pixel Font (OFL), see third_party/fusion-pixel/README.md
FUSION_VERSION = '2026.09.25'
FUSION_URL = (f'https://github.com/TakWolf/fusion-pixel-font/releases/download/{FUSION_VERSION}/'
              f'fusion-pixel-font-12px-monospaced-bdf-v{FUSION_VERSION}.zip')
FUSION_SHA256 = 'd75f5262f108757edb0f47ee8e3d2dfdfbecfd94558faf5ffb0c06dc5866fb3b'
FUSION_VARIANTS = ('zh_hans', 'zh_hant', 'ja', 'ko')
EXPECTED_SHA256 = '4ac3e2e1b8e3e14ce3078d0fe3f0a8c9641e04f65228a552ad5038c37c3260a9'
CJK_TTF = '/Resources/Fonts/CJK.ttf'


def digest(path, algo):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, algo).hexdigest()


def verified(path):
    return digest(path, 'sha1') == IPSW_SHA1 and digest(path, 'sha256') == IPSW_SHA256


def fusion_ok(path):
    return digest(path, 'sha256') == FUSION_SHA256


def fetch(url, dst, ok):
    """Download url to dst unless a good copy is already there; ok(path) checks the hash."""
    if os.path.exists(dst) and ok(dst):
        return
    print(f'== downloading {url}')
    part = dst + '.part'
    urllib.request.urlretrieve(url, part)
    if not ok(part):
        os.remove(part)
        sys.exit(f'{os.path.basename(dst)}: download does not match the pinned hash; not using it')
    os.replace(part, dst)


def fusion_fonts(out):
    """Extract the Fusion Pixel BDFs build_unified.py needs; returns their directory."""
    zip_path = os.path.join(out, os.path.basename(FUSION_URL))
    fetch(FUSION_URL, zip_path, fusion_ok)
    fdir = os.path.join(out, 'fusion-pixel')
    os.makedirs(fdir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for v in FUSION_VARIANTS:
            name = f'fusion-pixel-12px-monospaced-{v}.bdf'
            with open(os.path.join(fdir, name), 'wb') as f:
                f.write(z.read(name))
    return fdir


def main(ipsw=None, out=os.path.join(ROOT, 'build')):
    os.makedirs(out, exist_ok=True)
    if ipsw is None:
        ipsw = os.path.join(out, 'iPod_25.1.3.ipsw')
        fetch(IPSW_URL, ipsw, verified)
    if not verified(ipsw):
        sys.exit(f'{ipsw}: not iPod_25.1.3.ipsw (expected SHA1 {IPSW_SHA1})')
    print(f'== using {ipsw} (SHA1 verified)')
    fusion_dir = fusion_fonts(out)
    stock_dir = os.path.join(out, 'stock')
    os.makedirs(stock_dir, exist_ok=True)
    stock = os.path.join(stock_dir, 'Firmware-25.6.3')
    with zipfile.ZipFile(ipsw) as z, open(stock, 'wb') as f:
        f.write(z.read('Firmware-25.6.3'))
    stock_ttf = os.path.join(stock_dir, 'CJK.ttf')
    with open(stock_ttf, 'wb') as f:
        f.write(build_rsrc.read_file(open(stock, 'rb').read(), CJK_TTF))

    ttf = os.path.join(out, 'CJK.ttf')
    osos = os.path.join(out, 'osos.tmp')
    result = os.path.join(out, 'Firmware-25.6.3-cjk')
    print('== menus: extending CJK.ttf')
    extend_cjk_ttf.main(stock_ttf, ttf, os.path.join(ROOT, 'charsets', 'menu.txt'))
    print('== lyrics: rebuilding 12px CJK bitmap fonts')
    build_unified.main(stock, osos, fusion_dir,
                       os.path.join(ROOT, 'charsets', 'lyrics_extra.txt'))
    print('== rsrc: installing CJK.ttf')
    build_rsrc.main(osos, result, CJK_TTF, ttf)
    os.remove(osos)
    render_preview.main(stock, result, os.path.join(out, 'before-after.png'))

    sha = digest(result, 'sha256')
    print(f'\n{result}\nSHA256 {sha}')
    if sha == EXPECTED_SHA256:
        print('matches the released build')
    else:
        print(f'differs from the released build ({EXPECTED_SHA256}); '
              'expected if you changed charsets/ or the tools')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ipsw', help='local iPod_25.1.3.ipsw (default: download from Apple)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build'), help='build directory')
    args = ap.parse_args()
    main(args.ipsw, args.out)
