"""Verified VM scratch counters/position comparisons; no persistent variable array.

Context+30 is one native loop counter. Context+2C is the overwritten condition
result; context+34 is a script return address. None is a free project variable.
"""
import hashlib
import struct
from alundra_memory import parse_exe
from native_save_coverage import STOCK_SHA256

DISPATCH=0x8009B814
HANDLERS={0x6A:0x800403B8,0x6B:0x800403E4,0x6C:0x80040428,
          0x6D:0x8004046C,0x71:0x800404EC,0x73:0x80040518,0x74:0x80040534,
          0x78:0x800405F4,0x7D:0x800407FC}
WORDS={
 0x6A:(0x8C820114,0,0xACE2000C,0x8C820118,0,0xACE20010,
       0x8C82011C,0,0xACE20014,0x03E00008,0x24020001),
 0x6B:(0x8CE3000C,0x8C820114,0x8CC40000,0x00621823,0x04610002,0,
       0x00031823,0x90820002,0x90840001,0x00021200,0x00822025,
       0x00042400,0x0064182A,0x38630001,0x24020003,0x03E00008,0xACE3002C),
 0x6C:(0x8CE30010,0x8C820118,0x8CC40000,0x00621823,0x04610002,0,
       0x00031823,0x90820002,0x90840001,0x00021200,0x00822025,
       0x00042400,0x0064182A,0x38630001,0x24020003,0x03E00008,0xACE3002C),
 0x6D:(0x8CE30014,0x8C82011C,0x8CC40000,0x00621823,0x04610002,0,
       0x00031823,0x90820002,0x90840001,0x00021200,0x00822025,
       0x00042400,0x0064182A,0x38630001,0x24020003,0x03E00008,0xACE3002C),
 0x71:(0x8C820220,0,0xACE2002C,0x03E00008,0x24020001),
 0x73:(0x8CC20000,0,0x90420001,0,0xACE20030,0x03E00008,0x24020002),
 0x74:(0x8CE20030,0,0x2442FFFF,0x1C400003,0xACE20030,0x0801015C,
       0x24020003,0x8CC20000,0,0x90430002,0x90420001,0x00031A00,
       0x00431021,0x00021400,0x00021403,0x03E00008,0),
 0x78:(0x8CC20000,0,0x24420003,0xACE20034,0x8CC20000,0,
       0x90430002,0x90420001,0x00031A00,0x00431021,0x00021400,
       0x03E00008,0x00021403),
 0x7D:(0x8CE30034,0x8CC20000,0x03E00008,0x00621023),
}
CONTEXT_SITES={
 0x80023E10:(0x80042CC0,0x80042C34,0x80042C5C,0x80042CC0,0x80042CC0,0x80042CA0),
 0x80042C34:(0x8E420238,0,0x1040002A,0x26540234,0x8E420234),
 0x80042C5C:(0x8E420238,0,0x10400020,0x26540234,0x8E420234),
 0x80042CC0:(0x3C148015,0x26943340),
 0x8003EE5C:(0x8CE20008,0x8CC30000,0,0x10430004,0x00001021,0xACE30008,
              0x0800FBAA,0xACE0000C,0x8CE2000C,0,0x24430001,0xACE3000C,
              0x8CC30000,0,0x90630001,0,0x0043102A,0x38420001,
              0x00021040,0x03E00008,0),
}


def analyse(exe):
    if hashlib.sha256(exe).hexdigest()!=STOCK_SHA256:
        raise ValueError('VM scratch analysis requires fingerprinted stock ALUN_CD.EXE')
    info=parse_exe(exe);rows=[]
    for op,address in HANDLERS.items():
        table_offset=DISPATCH-info['load_address']+0x800+op*4
        if struct.unpack_from('<I',exe,table_offset)[0]!=address:
            raise ValueError(f'Dispatch mismatch for {op:02X}')
        offset=address-info['load_address']+0x800
        raw=struct.pack('<'+'I'*len(WORDS[op]),*WORDS[op])
        if exe[offset:offset+len(raw)]!=raw:raise ValueError(f'Handler mismatch for {op:02X}')
        rows.append(dict(opcode=f'0x{op:02X}',virtual_address=f'0x{address:08X}',
            exe_offset=f'0x{offset:X}',dispatch_exe_offset=f'0x{table_offset:X}',
            words=[f'{w:08X}' for w in WORDS[op]]))
    contexts=[]
    for address,words in CONTEXT_SITES.items():
        offset=address-info['load_address']+0x800
        if exe[offset:offset+4*len(words)]!=struct.pack('<'+'I'*len(words),*words):
            raise ValueError(f'Context site mismatch at {address:08X}')
        contexts.append(dict(virtual_address=f'0x{address:08X}',exe_offset=f'0x{offset:X}',
            words=[f'{w:08X}' for w in words]))
    return dict(module='ALUN_CD.EXE',sha256=STOCK_SHA256,build='Local USA-labelled Rev1 exact fingerprint',
        dispatch_table=f'0x{DISPATCH:08X}',handlers=rows,
        context_sites=contexts,global_scratch_address='0x80153340',
        retained_entity_context_relative='0x234',retained_modes=[1,2],
        global_initialized_modes=[0,3,4,5],
        native_context_fields=[dict(offset='0x0C',meaning='saved X',width_bits=32),
            dict(offset='0x10',meaning='saved Y',width_bits=32),dict(offset='0x14',meaning='saved Z',width_bits=32),
            dict(offset='0x2C',meaning='overwritten condition result',width_bits=32),
            dict(offset='0x30',meaning='single signed decrement/branch counter',width_bits=32),
            dict(offset='0x34',meaning='cached script return address',width_bits=32)],
        general_variable_array_proven=False,persistent_storage_proven=False,runtime_verified=False,
        limitations=['Scratch fields are not free persistent authoring variables',
            'One timer slot; nested/native timer commands can overwrite it',
            'Other handler uses and scheduler lifetime not exhaustively recovered'])


def _integer(value,lo,hi,label):
    if type(value) is not int or not lo<=value<=hi:raise ValueError(f'{label} must be {lo}..{hi}')
    return value


def signed32(value):
    value&=0xffffffff
    return value if value<0x80000000 else value-0x100000000


def counter_step(counter,relative_jump):
    """Exact 74 signed decrement/return model, including wrap; not time frames."""
    _integer(counter,-0x80000000,0x7fffffff,'Counter')
    _integer(relative_jump,-32768,32767,'Opcode-relative jump')
    result=signed32(counter-1)
    return result,relative_jump if result>0 else 3


def compile_counter_init(count):
    return bytes((0x73,_integer(count,0,255,'Native counter initializer')))


def compile_counter_step(relative_jump):
    return struct.pack('<Bh',0x74,_integer(relative_jump,-32768,32767,'Opcode-relative jump'))


def compile_counted_repeat(body,count,*,continuation_proven=False):
    """One scratch counter, bounded linear native commands, no nested counters.

    One iteration may finish in the same scheduler invocation. Bodies with
    waits/yields require an explicitly established retained continuation; global
    F/A/D/E scratch is otherwise reinitialized. This is not time in frames.
    """
    from event_editor import SIZES
    _integer(count,1,255,'Repeat count');body=bytes(body)
    if not body:raise ValueError('Repeat body must contain a command')
    # Existing bounded linear leaves only; no branches, exits, calls or timers.
    allowed={0,1,5,6,8,9,0x0A,0x0C,0x0D,0x10,0x11,0x12,0x1A,0x27,
             0x37,0x39,0x59,0x5C,0x75,0x98,0x99}
    cursor=0
    while cursor<len(body):
        op=body[cursor];size=SIZES.get(op)
        if op not in allowed or not size or cursor+size>len(body):
            raise ValueError('Repeat body must use complete linear leaves without nested counters/control flow')
        if op in (0,0x37,0x39) and not continuation_proven:
            raise ValueError('Yielding repeat body requires a proved retained native continuation context')
        cursor+=size
    return compile_counter_init(count)+body+compile_counter_step(-len(body))


def distance_condition(saved_position,current_position,threshold_raw):
    """6B..6D: signed wrapping absolute 16.16 distance >= signed(threshold<<16)."""
    for value in (saved_position,current_position):_integer(value,-0x80000000,0x7fffffff,'Position')
    _integer(threshold_raw,0,65535,'Raw threshold')
    distance=signed32(saved_position-current_position)
    if distance<0:distance=signed32(-distance)
    return int(distance>=signed32(threshold_raw<<16))


def compile_save_position():return bytes((0x6A,))


def compile_distance_condition(axis,world_pixels):
    if axis not in ('x','y','z'):raise ValueError('Distance axis must be x, y or z')
    # Avoid native negative signed thresholds while retaining raw model above.
    _integer(world_pixels,0,32767,'Nonnegative signed world-pixel threshold')
    return struct.pack('<BH',0x6B+'xyz'.index(axis),world_pixels)


def validate_leaf_models(exe):
    """Execute actual checked leaf words with delay slots; not PS1 gameplay."""
    from dream_gate_machine import GateMachine
    analyse(exe)
    class ScratchMachine(GateMachine):
        def step(self,pc):
            word=self.get(pc);op=word>>26;rs=word>>21&31;rt=word>>16&31;rd=word>>11&31
            imm=word&65535;si=imm if imm<32768 else imm-65536;target=None
            if op in (35,36):
                following=self.get(pc+4);next_op=following>>26
                # Every matched load delay uses a NOP or independent operands.
                reads={following>>21&31}
                if next_op in (0,4,5,40,41,43):reads.add(following>>16&31)
                assert rt not in reads or rt==0,'Unmodelled dependent load delay'
                self.r[rt]=self.get((self.r[rs]+si)&0xffffffff,4 if op==35 else 1)
            elif op==0 and word&63 in (35,37,3):
                function=word&63
                if function==35:self.r[rd]=self.r[rs]-self.r[rt]
                elif function==37:self.r[rd]=self.r[rs]|self.r[rt]
                else:self.r[rd]=signed32(self.r[rt])>>(word>>6&31)
            elif op==14:self.r[rt]=self.r[rs]^imm
            elif op==7:
                if signed32(self.r[rs])>0:target=pc+4+si*4
            else:return super().step(pc)
            self.r=[r&0xffffffff for r in self.r];self.r[0]=0
            return target
    cases=0
    def machine():
        m=ScratchMachine(exe);m.r[4]=0x1000;m.r[6]=0x2000;m.r[7]=0x3000;m.r[31]=0x4000
        m.put(0x2000,0x5000);return m
    for count in (*range(256),-1,-0x80000000,0x7fffffff):
        for displacement in (-32768,-2,0,3,32767):
            m=machine();m.put(0x3030,count);m.put(0x5001,displacement&65535,2)
            m.run(HANDLERS[0x74],{0x4000})
            expected=counter_step(count,displacement)
            assert (signed32(m.get(0x3030)),signed32(m.r[2]))==expected
            cases+=1
    for op in (0x6B,0x6C,0x6D):
        axis=op-0x6B
        for saved,current in ((0,0),(0,10<<16),(11<<16,0),(-0x80000000,0),(0x7fffffff,-1)):
            for threshold in (0,9,10,11,32767,32768,65535):
                m=machine();m.put(0x300c+4*axis,saved);m.put(0x1114+4*axis,current)
                m.put(0x5001,threshold,2);m.run(HANDLERS[op],{0x4000})
                assert m.get(0x302c)==distance_condition(saved,current,threshold)
                assert m.r[2]==3;cases+=1
    return dict(native_instruction_cases_passed=cases,runtime_verified=False,
                validation='Bounded integer instruction execution with checked load and branch delay slots')
