"""Patch the iPod's firmware partition in place: osos (fonts compiled into the OS) and rsrc
(resource FAT volume holding CJK.ttf).

The layout is read from the device's own partition directory (iTunes installs images without
the IPSW's 0x800-byte per-image headers, so offsets differ from the .ipsw file). For each image
the device copy must be byte-identical to the expected base image, or nothing is written. Only
sectors whose content changes are written, then read back and compared. Music is untouched.

usage: sudo python3 -I install_firmware.py <firmware partition, e.g. /dev/rdisk6s2>
           <expected-current firmware file> <new firmware file> <backup file> [--write]
Without --write it only verifies and reports what it would change.
"""
import os
import struct
import sys

SECTOR = 512
DIR = 0x4200
FILE_HDR = 0x800  # per-image header in the .ipsw firmware file
DEV_HDR = 0x200   # on the device, image data starts 0x200 past the directory's devOffset
IMAGES = (b'soso', b'crsr')  # osos, rsrc (stored byte-reversed)


def read(fd, off, n):
    buf = b''
    while len(buf) < n:
        chunk = os.pread(fd, min(1 << 20, n - len(buf)), off + len(buf))
        if not chunk:
            break
        buf += chunk
    return buf


def entry(buf, ident):
    for i in range(16):
        e = DIR + 40 * i
        if buf[e:e + 4] != b'!ATA':
            break
        if buf[e + 4:e + 8] == ident:
            return e, struct.unpack_from('<6I', buf, e + 8)
    raise SystemExit(f'no {ident[::-1].decode()} entry in partition directory')


def file_image(fw, ident, length):
    """Image bytes from an .ipsw-layout firmware file, aligned to the device's layout."""
    _e, (_z, dev, flen, _a, ent, _c) = entry(fw, ident)
    start = dev + FILE_HDR + ent
    img = fw[start:start + length]
    rest = fw[start + length:dev + FILE_HDR + flen]
    assert len(img) == length and not any(rest), f'{ident[::-1].decode()}: file image does not fit device layout'
    return img


def main():
    args = [a for a in sys.argv[1:] if a != '--write']
    write = '--write' in sys.argv
    if len(args) != 4:
        sys.exit(__doc__)
    part, base_path, new_path, backup = args
    base = open(base_path, 'rb').read()
    target = open(new_path, 'rb').read()

    fd = os.open(part, os.O_RDWR if write else os.O_RDONLY)
    try:
        head = read(fd, 0, DIR + SECTOR)
        plans = []
        for ident in IMAGES:
            ent, (_z, dev_off, length, _addr, dev_entry, chk) = entry(head, ident)
            assert dev_entry == 0, 'unexpected entryOffset on device'
            plans.append((ident, ent, dev_off + DEV_HDR, length, chk))
        span = max(-(-(d + n) // SECTOR) * SECTOR for _i, _e, d, n, _c in plans)
        disk = read(fd, 0, span)
        assert len(disk) == span, 'partition shorter than expected'

        new = bytearray(disk)
        for ident, ent, data, length, chk in plans:
            name = ident[::-1].decode()
            want_base, want_new = file_image(base, ident, length), file_image(target, ident, length)
            cur = disk[data:data + length]
            new_chk = sum(want_new) & 0xFFFFFFFF
            if cur == want_new and chk == new_chk:
                print(f'{name}: already the new image')
                continue
            assert cur == want_base, f'{name}: device image differs from expected base -- refusing'
            assert chk == sum(want_base) & 0xFFFFFFFF, f'{name}: device checksum mismatch -- refusing'
            new[data:data + length] = want_new
            struct.pack_into('<I', new, ent + 28, new_chk)
            print(f'{name}: verified base at {data:#x}+{length:#x}; checksum {chk:#010x} -> {new_chk:#010x}')

        sectors = sorted({i // SECTOR for i in range(span) if disk[i] != new[i]})
        if not sectors:
            print('Nothing to do.')
            return
        print(f'{len(sectors)} sectors to write, first {sectors[0] * SECTOR:#x}, last {sectors[-1] * SECTOR:#x}')
        if not write:
            print('Dry run only; re-run with --write to apply.')
            return

        with open(backup, 'wb') as b:
            b.write(disk)
        print(f'Backed up first {span:#x} bytes of partition to {backup}')
        for s in sectors:
            os.pwrite(fd, bytes(new[s * SECTOR:(s + 1) * SECTOR]), s * SECTOR)
        os.fsync(fd)
        assert read(fd, 0, span) == bytes(new), 'readback mismatch!'
        print('Written and verified by readback.')
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
