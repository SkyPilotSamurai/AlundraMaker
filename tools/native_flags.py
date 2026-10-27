"""Unsigned 16-bit operand mapping from ALUN_CD.EXE 0x8008405C.
Static reconstruction; does not classify arbitrary script operands as flags.
"""


def locate_flag(code):
    if not 0 <= code <= 0xFFFF:
        raise ValueError('Expected unsigned 16-bit operand')
    base = 0x801E6378 if code & 0x8000 else 0x801DD334
    word = base + ((code >> 3) & 0xFFC)
    bit = code & 31
    return dict(word_address=word, word_mask=1 << bit,
                byte_address=word + bit // 8, byte_mask=1 << (bit & 7),
                bank=1 if code & 0x8000 else 0)
