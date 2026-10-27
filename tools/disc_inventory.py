"""Inventory a single-track MODE2/2352 ISO9660 disc; extract selected files locally.

Retail output belongs only in private-inputs/. No source image is modified.
Reject unsupported sector forms, interleaving and multi-extent files.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def both32(data, offset):
    little = struct.unpack_from('<I', data, offset)[0]
    if little != struct.unpack_from('>I', data, offset + 4)[0]:
        raise ValueError('ISO endian copies disagree')
    return little


def record(data):
    if len(data) < 34 or data[0] != len(data):
        raise ValueError('Invalid directory record')
    if data[1] or data[25] & 0x80 or data[26] or data[27]:
        raise ValueError('Extended attributes/multi-extent/interleaved files unsupported')
    return dict(lba=both32(data, 2), size=both32(data, 10),
                directory=bool(data[25] & 2), name=data[33:33 + data[32]])


class Disc:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.stat().st_size % 2352:
            raise ValueError('Not an integral number of 2352-byte sectors')
        self.handle = self.path.open('rb')

    def read(self, lba, size):
        count = (size + 2047) // 2048
        self.handle.seek(lba * 2352)
        blob = self.handle.read(count * 2352)   # one read (was one seek + read per sector)
        if len(blob) != count * 2352:
            raise ValueError('Invalid/truncated raw sector')
        view = memoryview(blob); sync = b'\x00' + b'\xff' * 10 + b'\x00'
        chunks = []
        for at in range(0, len(blob), 2352):
            raw = view[at:at + 2352]
            if raw[:12] != sync:
                raise ValueError('Invalid/truncated raw sector')
            if raw[15] != 2 or raw[16:20] != raw[20:24] or raw[18] & 0x20:
                raise ValueError('Expected MODE2 Form1 sector')
            chunks.append(raw[24:2072])
        return b''.join(chunks)[:size]

    def inventory(self):
        pvd = self.read(16, 2048)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('Expected ISO9660 primary volume descriptor')
        if struct.unpack_from('<H', pvd, 128)[0] != 2048:
            raise ValueError('Unsupported logical block size')
        rows, visited = [], set()

        def walk(entry, parent):
            if entry['lba'] in visited:
                raise ValueError('Repeated/cyclic directory extent')
            visited.add(entry['lba'])
            data, pos = self.read(entry['lba'], entry['size']), 0
            while pos < len(data):
                length = data[pos]
                if not length:
                    pos = (pos // 2048 + 1) * 2048
                    continue
                child = record(data[pos:pos + length])
                pos += length
                if child['name'] in (b'\x00', b'\x01'):
                    continue
                name = child.pop('name').decode('ascii').split(';')[0]
                if name in ('.', '..') or any(c in name for c in '/\\:'):
                    raise ValueError('Unsafe ISO filename')
                child['path'] = parent + name
                rows.append(child)
                if child['directory']:
                    walk(child, child['path'] + '/')
        walk(record(pvd[156:156 + pvd[156]]), '')
        return pvd[40:72].decode('ascii').strip(), rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extract', nargs='*', default=[])
    args = parser.parse_args()
    disc = Disc(args.image)
    volume, rows = disc.inventory()
    with args.image.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    selected = {name.upper() for name in args.extract}
    found = set()
    for row in rows:
        if row['directory'] or row['path'].upper() not in selected:
            continue
        content = disc.read(row['lba'], row['size'])
        row['sha256'] = hashlib.sha256(content).hexdigest()
        target = Path('private-inputs/disc') / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'Refusing to overwrite differing input: {target}')
        target.write_bytes(content)
        found.add(row['path'].upper())
        if content[:8] == b'PS-X EXE':
            from alundra_memory import parse_exe
            row['exe_header'] = parse_exe(content)
    if selected - found:
        raise ValueError(f'Files not found: {sorted(selected - found)}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(image=args.image.name, sha256=digest,
        volume=volume, revision_status='not independently matched to a revision database',
        files=rows), indent=2) + '\n', encoding='utf-8')
    print(f'Volume {volume}: {len(rows)} entries; extracted {len(found)} files; SHA256 {digest}')


if __name__ == '__main__':
    main()
