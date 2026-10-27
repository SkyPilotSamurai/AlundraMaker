"""CD-ROM Mode 2 Form 1 sector error codes (EDC and ECC P/Q), so a few
changed sectors of a built disc image can be rewritten in place instead of
rebuilding the whole image (mod_export fast rebuild)."""

def _edc_table():
    table = []
    for i in range(256):
        edc = i
        for _ in range(8):
            edc = (edc >> 1) ^ (0xD8018001 if edc & 1 else 0)
        table.append(edc)
    return table


EDC_TABLE = _edc_table()
ECC_F = [0] * 256
ECC_B = [0] * 256
for _i in range(256):
    _j = ((_i << 1) ^ (0x11D if _i & 0x80 else 0)) & 0xFF
    ECC_F[_i] = _j
    ECC_B[_i ^ _j] = _i


def edc(data):
    value = 0; table = EDC_TABLE
    for byte in data:
        value = table[(value ^ byte) & 0xFF] ^ (value >> 8)
    return value


def _ecc_block(src, major_count, minor_count, major_mult, minor_inc, dest, dest_at):
    size = major_count * minor_count; f = ECC_F; b = ECC_B
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        ecc_a = ecc_b = 0
        for _ in range(minor_count):
            temp = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            ecc_a ^= temp; ecc_b ^= temp; ecc_a = f[ecc_a]
        ecc_a = b[f[ecc_a] ^ ecc_b]
        dest[dest_at + major] = ecc_a
        dest[dest_at + major + major_count] = ecc_a ^ ecc_b


def mode2_form1(sector):
    """Recompute EDC and ECC of a raw 2352-byte Mode 2 Form 1 sector (bytearray)."""
    if len(sector) != 2352 or sector[15] != 2 or sector[18] & 0x20:
        raise ValueError('Expected a MODE2 Form1 sector')
    sector[2072:2076] = edc(sector[16:2072]).to_bytes(4, 'little')
    address = bytes(sector[12:16]); sector[12:16] = b'\0\0\0\0'   # ECC skips the address in mode 2
    _ecc_block(sector[12:2076], 86, 24, 2, 86, sector, 2076)            # P parity
    _ecc_block(sector[12:2248], 52, 43, 86, 88, sector, 2248)           # Q parity
    sector[12:16] = address
    return sector


def mode2_form1_many(sectors):
    """mode2_form1 for many sectors at once (2026-10-15: the fast rebuild spent
    most of its time here, ~1 ms per sector in pure Python). With numpy every
    sector is done together, byte position by byte position; without it, one by
    one as before. Results are identical (tests/test_cd_sector_many.py)."""
    sectors = list(sectors)
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is None or len(sectors) < 16:
        return [mode2_form1(s) for s in sectors]
    for s in sectors:
        if len(s) != 2352 or s[15] != 2 or s[18] & 0x20:
            raise ValueError('Expected a MODE2 Form1 sector')
    a = np.frombuffer(b''.join(bytes(s) for s in sectors), dtype=np.uint8).reshape(len(sectors), 2352).copy()
    table = np.array(EDC_TABLE, dtype=np.uint32)
    value = np.zeros(len(sectors), dtype=np.uint32)
    for i in range(16, 2072):
        value = table[(value ^ a[:, i]) & 0xFF] ^ (value >> 8)
    a[:, 2072:2076] = value.view(np.uint8).reshape(-1, 4) if value.dtype.byteorder in ('<', '=') and np.little_endian else \
        np.stack([(value >> (8 * k)) & 0xFF for k in range(4)], axis=1).astype(np.uint8)
    address = a[:, 12:16].copy(); a[:, 12:16] = 0
    f = np.array(ECC_F, dtype=np.uint8); b = np.array(ECC_B, dtype=np.uint8)

    def block(src_len, major_count, minor_count, major_mult, minor_inc, dest_at):
        src = a[:, 12:12 + src_len]
        size = major_count * minor_count
        majors = np.arange(major_count)
        index = (majors >> 1) * major_mult + (majors & 1)
        ecc_a = np.zeros((len(sectors), major_count), dtype=np.uint8)
        ecc_b = np.zeros((len(sectors), major_count), dtype=np.uint8)
        for _ in range(minor_count):
            temp = src[:, index]
            index = index + minor_inc
            index = np.where(index >= size, index - size, index)
            ecc_a ^= temp; ecc_b ^= temp; ecc_a = f[ecc_a]
        ecc_a = b[f[ecc_a] ^ ecc_b]
        a[:, dest_at:dest_at + major_count] = ecc_a
        a[:, dest_at + major_count:dest_at + 2 * major_count] = ecc_a ^ ecc_b

    block(2064, 86, 24, 2, 86, 2076)      # P parity (reads 12..2076)
    block(2236, 52, 43, 86, 88, 2248)     # Q parity (reads 12..2248, P included)
    a[:, 12:16] = address
    out = []
    for s, row in zip(sectors, a):
        s[:] = row.tobytes(); out.append(s)
    return out
