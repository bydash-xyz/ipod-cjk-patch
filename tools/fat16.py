"""Minimal FAT12/16 reader/writer for the iPod rsrc volume (supports long file names)."""
import os
import struct
import sys


class Fat16:
    def __init__(self, data):
        self.d = data
        (self.bps, self.spc, self.rsv, self.nfats, self.nroot, tot16, _media,
         self.fatsz) = struct.unpack_from('<HBHBHHBH', data, 11)
        self.fat_off = self.rsv * self.bps
        self.root_off = self.fat_off + self.nfats * self.fatsz * self.bps
        self.data_off = self.root_off + self.nroot * 32
        self.csize = self.spc * self.bps
        nclus = ((tot16 or struct.unpack_from('<I', data, 32)[0]) * self.bps - self.data_off) // self.csize
        self.fat12 = nclus < 4085  # mkfs labels lie; cluster count decides

    def next_clus(self, clus):
        if not self.fat12:
            return struct.unpack_from('<H', self.d, self.fat_off + 2 * clus)[0]
        v = struct.unpack_from('<H', self.d, self.fat_off + clus * 3 // 2)[0]
        v = v >> 4 if clus & 1 else v & 0xFFF
        return v | 0xF000 if v >= 0xFF8 else v

    def chain(self, clus):
        seen = set()
        while 2 <= clus < 0xFFF8 and clus not in seen:
            seen.add(clus)
            yield clus
            clus = self.next_clus(clus)

    def read_clusters(self, clus):
        return b''.join(self.d[self.data_off + (c - 2) * self.csize:
                               self.data_off + (c - 1) * self.csize]
                        for c in self.chain(clus))

    def entries(self, raw):
        lfn = {}
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5:
                lfn = {}
                continue
            if e[11] == 0x0F:
                seq = e[0] & 0x1F
                lfn[seq] = (e[1:11] + e[14:26] + e[28:32]).decode('utf-16le', 'replace')
                continue
            short = e[0:8].decode('latin1').rstrip()
            ext = e[8:11].decode('latin1').rstrip()
            name = ''.join(lfn[k] for k in sorted(lfn)).split('\0')[0] if lfn else (
                short + ('.' + ext if ext else ''))
            lfn = {}
            attr = e[11]
            clus = struct.unpack_from('<H', e, 26)[0]
            size = struct.unpack_from('<I', e, 28)[0]
            if attr & 0x08:
                continue
            yield name, attr, clus, size

    def walk(self, raw=None, path=''):
        if raw is None:
            raw = self.d[self.root_off:self.data_off]
        for name, attr, clus, size in self.entries(raw):
            if name in ('.', '..'):
                continue
            p = f'{path}/{name}'
            if attr & 0x10:
                yield p, None, clus, 0
                yield from self.walk(self.read_clusters(clus), p)
            else:
                yield p, 'f', clus, size

    def extract(self, out):
        for p, kind, clus, size in self.walk():
            dst = os.path.join(out, p.lstrip('/'))
            if kind is None:
                os.makedirs(dst, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as f:
                    f.write(self.read_clusters(clus)[:size])
                print(f'{size:9d}  {p}')

    def find_entry(self, path):
        """Return byte offset of the 32-byte short dir entry for `path` (e.g. /Resources/Fonts/CJK.ttf)."""
        parts = path.strip('/').split('/')
        spans = [(self.root_off, self.data_off)]
        for depth, want in enumerate(parts):
            found = None
            for start, end in spans:
                lfn = {}
                for o in range(start, end, 32):
                    e = self.d[o:o + 32]
                    if e[0] == 0:
                        break
                    if e[0] == 0xE5:
                        lfn = {}
                        continue
                    if e[11] == 0x0F:
                        lfn[e[0] & 0x1F] = (e[1:11] + e[14:26] + e[28:32]).decode('utf-16le', 'replace')
                        continue
                    short = e[0:8].decode('latin1').rstrip()
                    ext = e[8:11].decode('latin1').rstrip()
                    name = ''.join(lfn[k] for k in sorted(lfn)).split('\0')[0] if lfn else (
                        short + ('.' + ext if ext else ''))
                    lfn = {}
                    if name == want:
                        found = o
                        break
                if found is not None:
                    break
            if found is None:
                raise FileNotFoundError(path)
            if depth == len(parts) - 1:
                return found
            clus = struct.unpack_from('<H', self.d, found + 26)[0]
            spans = [(self.data_off + (c - 2) * self.csize, self.data_off + (c - 1) * self.csize)
                     for c in self.chain(clus)]

    def read_file(self, path):
        ent = self.find_entry(path)
        clus, size = struct.unpack_from('<HI', self.d, ent + 26)
        return self.read_clusters(clus)[:size]


class Fat12Writer(Fat16):
    """In-place file replacement for a FAT12/16 image held in a bytearray."""

    def __init__(self, data):
        super().__init__(data)
        assert isinstance(data, bytearray)
        self.nclus = ((struct.unpack_from('<H', data, 19)[0] or struct.unpack_from('<I', data, 32)[0])
                      * self.bps - self.data_off) // self.csize + 2

    def set_clus(self, clus, val):
        for n in range(self.nfats):
            base = self.fat_off + n * self.fatsz * self.bps
            if not self.fat12:
                struct.pack_into('<H', self.d, base + 2 * clus, val)
                continue
            o = base + clus * 3 // 2
            cur = struct.unpack_from('<H', self.d, o)[0]
            cur = (cur & 0x000F) | (val << 4) if clus & 1 else (cur & 0xF000) | val
            struct.pack_into('<H', self.d, o, cur & 0xFFFF)

    def replace_file(self, path, content):
        """Overwrite a file's content, growing its cluster chain into free clusters as needed."""
        ent = self.find_entry(path)
        first = struct.unpack_from('<H', self.d, ent + 26)[0]
        chain = list(self.chain(first))
        need = (len(content) + self.csize - 1) // self.csize
        free = (c for c in range(2, self.nclus) if self.next_clus(c) == 0)
        while len(chain) < need:
            c = next(free, None)
            if c is None:
                raise OSError('volume full')
            self.set_clus(chain[-1], c)
            self.set_clus(c, 0xFFF if self.fat12 else 0xFFFF)
            chain.append(c)
        # a shorter file keeps its surplus clusters (zeroed); fine for one-off patching
        for i, c in enumerate(chain):
            o = self.data_off + (c - 2) * self.csize
            piece = content[i * self.csize:(i + 1) * self.csize]
            self.d[o:o + self.csize] = piece + b'\0' * (self.csize - len(piece))
        struct.pack_into('<I', self.d, ent + 28, len(content))


if __name__ == '__main__':
    # usage: fat16.py <file> <volume offset> <out dir>  -- extract every file
    fw, off, out = sys.argv[1], int(sys.argv[2], 0), sys.argv[3]
    with open(fw, 'rb') as f:
        data = f.read()[off:]
    Fat16(data).extract(out)
