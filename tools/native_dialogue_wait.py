"""Native 39 dialogue wait; this helper does not establish process continuation."""
import hashlib
import struct
from alundra_memory import parse_exe
from native_save_coverage import STOCK_SHA256

SITES = {
    0x8003EEF0: (0x27BDFFE8, 0xAFBF0010, 0x0C010C02, 0,
                 0x8FBF0010, 0x2C420001, 0x03E00008, 0x27BD0018),
    0x80043008: (0x27BDFFE8, 0xAFBF0010, 0x0C0117E3, 0,
                 0x8FBF0010, 0x27BD0018, 0x03E00008, 0),
    0x80045F8C: (0x3C028010, 0x8C426AFC, 0, 0x30420004,
                 0x03E00008, 0x0002102B),
}


def analyse(exe):
    if hashlib.sha256(exe).hexdigest() != STOCK_SHA256:
        raise ValueError('Dialogue wait evidence requires the exact stock executable')
    info = parse_exe(exe)
    def offset(address): return address - info['load_address'] + 0x800
    if struct.unpack_from('<I', exe, offset(0x8009B814 + 0x39 * 4))[0] != 0x8003EEF0:
        raise ValueError('Dialogue wait dispatch changed')
    for address, words in SITES.items():
        if exe[offset(address):offset(address) + len(words) * 4] != struct.pack('<' + 'I' * len(words), *words):
            raise ValueError('Dialogue wait native instructions changed')
    return dict(module='stock ALUN_CD.EXE', sha256=STOCK_SHA256, opcode='39',
        dispatch='8009B814', handler='8003EEF0', dialogue_flags='80106AFC',
        semantic='Return0/yield without cursor advance while dialogue flags mask0x04 (bit2) is set; return1/advance when clear',
        sites=[dict(address=f'{address:08X}', words=[f'{w:08X}' for w in words]) for address, words in SITES.items()],
        new_authoring_scope='Graphic-free Player Touch native B context only',
        runtime_verified=False,
        limits=['F/D continuation is not established by this one-byte wait',
                'Source IsDialogFinished naming is not a reason to invert native bit semantics'])


def dialogue_wait_step(flags):
    if type(flags) is not int or not 0 <= flags <= 0xFFFFFFFF:
        raise ValueError('Native dialogue flags must be unsigned32')
    return 0 if flags & 4 else 1


def compile_dialogue_wait(): return b'\x39'
