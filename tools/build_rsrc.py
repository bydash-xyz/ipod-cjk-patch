"""Replace a file inside the firmware's rsrc FAT volume and fix the rsrc checksum.

usage: build_rsrc.py <base firmware file> <out firmware file> <volume path> <new file>
e.g.   build_rsrc.py build/osos.tmp build/Firmware-25.6.3-cjk /Resources/Fonts/CJK.ttf build/CJK.ttf
"""
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import ipodfw  # noqa: E402
from fat16 import Fat12Writer  # noqa: E402


def read_file(fw, vol_path):
    """Contents of a file in the firmware's rsrc volume."""
    start, length = ipodfw.rsrc_volume(fw)
    return Fat12Writer(bytearray(fw[start:start + length])).read_file(vol_path)


def main(base, out, vol_path, new_file):
    fw = bytearray(open(base, 'rb').read())
    assert ipodfw.checksum_ok(fw, 'rsrc'), 'base rsrc checksum mismatch'
    start, length = ipodfw.rsrc_volume(fw)
    vol = bytearray(fw[start:start + length])
    Fat12Writer(vol).replace_file(vol_path, open(new_file, 'rb').read())
    fw[start:start + length] = vol
    old, new = ipodfw.fix_checksum(fw, 'rsrc')
    open(out, 'wb').write(fw)
    print(f'rsrc: replaced {vol_path}; checksum {old:#010x} -> {new:#010x}; wrote {out}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:5])
