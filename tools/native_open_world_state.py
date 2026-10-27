"""Original injected post-reset initialization for the bounded world-access mod."""
import struct
from project_state_runtime import _Mips
from native_lr_swaps import offset

HOOK=0x80031D34
RESET=0x80083DA0


def validate(exe,stock,flags,variants):
    for start,size in ((HOOK,8),(RESET,0x80083FC4-RESET)):
        a=offset(exe,start,size);b=offset(stock,start,size)
        current=bytearray(exe[a:a+size]);expected=stock[b:b+size]
        # The editor's private project-state initializer also relocates the
        # native descending stack below its injected code. That one exact
        # stack-top immediate is inside the reset routine's surrounding range;
        # accept its verified relocation while still comparing every other
        # byte against stock. Open World then composes another prepend and
        # recalculates the same immediate for the combined allocation.
        from native_injection_stack import STACK_SITE
        if start<=STACK_SITE and STACK_SITE+4<=start+size:
            relative=STACK_SITE-start
            load=struct.unpack_from('<I',exe,0x18)[0]
            relocated=struct.pack('<I',0x34840000|((load-16)&0xffff))
            if current[relative:relative+4]==relocated:
                current[relative:relative+4]=expected[relative:relative+4]
        if bytes(current)!=expected:
            raise ValueError(f'Open-world native new-game reset code conflicts at {start:08X}')
    for row in flags:
        operand=row['operand']
        if type(operand) is not int or not 0<=operand<=0x7FF:
            raise ValueError('Open-world flag is outside initialized persistent bank')
        if int(row['byte_address'],16)!=0x801DD334+operand//8 or row['byte_mask']!=1<<(operand%8):
            raise ValueError('Open-world flag address/mask does not match the native bank')
    for row in variants:
        address=int(row['address'],16)
        if (row['width_bits']!=16 or address%2 or not 0x801DD434<=address<0x801DD734
                or type(row['value']) is not int or not 0<=row['value']<=0x2FF):
            raise ValueError('Open-world variant store is outside the bounded native map-variant area')


def emit_wrapper(flags,variants):
    m=_Mips();m.i(9,29,29,-24);m.i(43,29,31,16)
    m.words.extend([0x0C000000|((RESET>>2)&0x3FFFFFF),0])
    # Read-modify-write bytes preserve all flags set by the native initializer.
    for row in flags:
        m.li(8,int(row['byte_address'],16));m.load(9,8,0,36)
        m.i(13,9,9,row['byte_mask']);m.i(40,8,9,0)
    for row in variants:
        m.li(8,int(row['address'],16));m.i(9,0,9,row['value']);m.i(41,8,9,0)
    m.load(31,29,16);m.i(9,29,29,24);m.words.extend([0x03E00008,0])
    return m.finish()
