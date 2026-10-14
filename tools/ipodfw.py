"""Image directory of an iPod 5G/5.5G firmware file in .ipsw layout (e.g. Firmware-25.6.3).

The directory at 0x4200 holds 40-byte '!ATA' entries: ident (byte-reversed name, 'soso' = osos),
then u32 zero, devOffset, length, address, entryOffset, checksum. In the .ipsw file each image's
data starts at devOffset + 0x800 (on the device: + 0x200, see install_firmware.py). The checksum
is the 32-bit byte sum of the image data.
"""
import struct

DIR = 0x4200
IMG_HDR = 0x800


def entry(fw, name):
    """Return (directory entry offset, (zero, dev, length, addr, entry, checksum)) for `name`."""
    ident = name.encode()[::-1]
    for i in range(16):
        e = DIR + 40 * i
        if fw[e:e + 4] != b'!ATA':
            break
        if fw[e + 4:e + 8] == ident:
            return e, struct.unpack_from('<6I', fw, e + 8)
    raise KeyError(f'no {name} image in firmware directory')


def data_range(fw, name):
    """(start, end) of an image's data in the file."""
    _e, (_z, dev, length, _a, _ent, _c) = entry(fw, name)
    return dev + IMG_HDR, dev + IMG_HDR + length


def checksum_ok(fw, name):
    a, b = data_range(fw, name)
    return sum(fw[a:b]) & 0xFFFFFFFF == entry(fw, name)[1][5]


def fix_checksum(fw, name):
    """Recompute an image's checksum in the directory; returns (old, new)."""
    e, (*_x, old) = entry(fw, name)
    a, b = data_range(fw, name)
    new = sum(fw[a:b]) & 0xFFFFFFFF
    struct.pack_into('<I', fw, e + 28, new)
    return old, new


def rsrc_volume(fw):
    """(start, length) of the FAT volume inside the rsrc image."""
    _e, (_z, dev, _len, _a, ent, _c) = entry(fw, 'rsrc')
    start = dev + IMG_HDR + ent
    bps, = struct.unpack_from('<H', fw, start + 11)
    sectors, = struct.unpack_from('<H', fw, start + 19)
    return start, sectors * bps
