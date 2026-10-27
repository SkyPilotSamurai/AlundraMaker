"""Exact-site native save staging coverage and checksum reconstruction.

This establishes the copied span in the fingerprinted ALUN_CD.EXE, not free
flag allocation, memory-card filesystem offsets or runtime save/load success.
"""
import hashlib
import struct
from alundra_memory import parse_exe

STOCK_SHA256='12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3'
SIGNATURES={
    0x80031AEC:(0x3C10801E,0x2610D324),
    0x80031B1C:(0x2604FFB4,0x24050758),
    0x80031B34:(0x0C018385,0x24060001),
    0x80060E38:(0x3C01801E,0xAC2493E8,0x3C018015,0xAC252BDC),
    0x80063718:(0x3C048012,0x24842898,0x00128100,0x02128023,0x001080C0,
                0x02128023,0x00108080,0x02128023,0x00108080,0x02042021),
    0x80063740:(0x3C05801E,0x8CA593E8,0x3C068015,0x8CC62BDC,0x0C02119D,0x00008821),
    0x800637F4:(0x0C018E30,0x24041FFC,0x3C108012,0x26104694,0xAE020000),
    0x80063810:(0x0C01802A,0x2606E004),
    0x80060158:(0x02002021,0x0C0210AB,0x24062000),
    0x80084684:(0x90A20000,0x24A50001,0x24C6FFFF,0xA0820000,0x1CC0FFFB,0x24840001),
    0x800638C8:(0x3C088000,0x3C0704C1,0x34E71DB7,0x3C068012,0x24C62698),
    0x800638C0:(0x10800019,0x2403FFFF,0x3C088000,0x3C0704C1,0x34E71DB7,
                0x3C068012,0x24C62698,0x00862021,0x90C20000,0x00002821,
                0x00021600,0x00621826,0x00681024,0x10400003,0x00031040,
                0x08018E42,0x00471826,0x00031840,0x24A50001,0x2CA20008,
                0x1440FFF8,0x00681024,0x24C60001,0x00C4102B,0x1440FFEF,
                0x00000000,0x03E00008,0x00031027),
    0x80063928:(0x03E00008,0x00031027),
    0x80029B68:(0x80010000,),
    0x80083E3C:(0x3C06801E,0x24C6D2D8,0x24C80750),
}


def preflight_words(exe):
    """Check encoded sites using the EXE's own load mapping; no revision delta."""
    info=parse_exe(exe);load=info['load_address'];size=info['load_size'];rows=[]
    for address,words in sorted(SIGNATURES.items()):
        offset=address-load+0x800
        expected=struct.pack('<'+'I'*len(words),*words)
        if offset<0x800 or offset+len(expected)>0x800+size or exe[offset:offset+len(expected)]!=expected:
            raise ValueError(f'Native save site mismatch at 0x{address:08X}')
        rows.append(dict(virtual_address=f'0x{address:08X}',exe_offset=f'0x{offset:X}',
                         words=[f'{word:08X}' for word in words]))
    return rows


def analyse(exe):
    digest=hashlib.sha256(exe).hexdigest()
    if digest!=STOCK_SHA256:raise ValueError('Save coverage requires fingerprinted stock ALUN_CD.EXE')
    rows=preflight_words(exe)
    return dict(module='ALUN_CD.EXE',sha256=digest,
        build='Local USA-labelled Rev1 input; exact module fingerprint, no revision delta',
        address_space='PS1 virtual + EXE file offsets',
        state_source='0x801DD2D8',state_copy_bytes=0x758,flag_bank_start='0x801DD334',
        flag_bank_end_inclusive='0x801DD433',flag_bank_bytes=256,
        flag_offset_within_native_state=0x5c,flag_bank_fully_within_state_copy=True,
        native_slot_staging_base='0x80122898',native_slot_stride=0x76c,
        card_blob_base='0x80122698',card_blob_bytes=0x2000,
        checksum_span_bytes=0x1ffc,checksum_result_address='0x80124694',
        checksum_polynomial='0x04C11DB7',checksum_initial='0xFFFFFFFF',
        checksum_final_xor='0xFFFFFFFF',checksum_reflected=False,
        independent_temporary_state_copy_base='0x80010000',
        native_sites=rows,confidence='native static encoded instructions and span arithmetic',
        runtime_verified=False,unused_flag_bits_proven=False,
        memory_card_filesystem_offsets_established=False,
        limits=['No unused/persistent project-bit allocation established',
                'No actual card readback, reload or emulator state comparison',
                'Staging blob offsets are distinct from emulator full-card file offsets'])


def native_checksum(blob):
    """Nonreflected CRC reconstructed from native 0x800638C0 body."""
    crc=0xffffffff
    for value in bytes(blob):
        crc^=value<<24
        for _ in range(8):
            crc=((crc<<1)^ (0x04c11db7 if crc&0x80000000 else 0))&0xffffffff
    return crc^0xffffffff


def catalogue_entries(report):
    """Standalone catalogue-compatible records; never rewrites historical rows."""
    common=dict(module=report['module'],module_sha256=report['sha256'],
                build=report['build'],confidence=report['confidence'],
                runtime_verified=False,limitations=report['limits'])
    entries=[]
    def add(key,group,name,address,details):
        entries.append(dict(id='native-save-20261005:'+key,group=group,name=name,
            addresses=address,status='Static evidence; no save/readback validation',
            source='data/2026-10-05-native-save-flag-coverage.json',
            details=dict(common,**details)))
    for key,name,address,width,refs,note in (
        ('source-pointer','Native save source pointer','0x801D93E8',32,
         ['0x80060E3C SW','0x80063744 LW'],'Pointer to state span, not state field width'),
        ('source-length','Native save copy length','0x80152BDC',32,
         ['0x80060E44 SW','0x8006374C LW'],'0x758 bytes selected by caller at 0x80031B20'),
        ('state','Live native save state span','0x801DD2D8',8,
         ['0x80031B1C address formation','0x80063750 calls 0x80084674','0x80084684 LBU / 0x80084690 SB'],
         '0x758-byte byte-copy span; individual fields may have other native widths'),
        ('flag-span','Flag bank coverage in native save copy','0x801DD334..0x801DD433',8,
         ['0x80031B1C','0x80063740..0x80063754','0x80084684..0x80084698'],
         'Byte-copy width only; native flag handlers access 32-bit words'),
        ('slot-staging','Selected native save record staging address','0x80122898 + slot*0x76C',8,
         ['0x80063718..0x8006373C','0x80063750'],
         'Derived slot formula; no full emulator memory-card file offset'),
        ('blob','Native card block staging buffer','0x80122698',8,
         ['0x800638D4..0x800638E0','0x80063814','0x8006015C..0x80060160'],
         '0x2000-byte write source; first 0x1FFC bytes checksummed'),
        ('checksum-result','Native save CRC result','0x80124694',32,
         ['0x800637FC..0x80063804 SW'],
         'Staging buffer + 0x1FFC; not a full memory-card file offset'),
        ('temporary-pointer','Native temporary-state buffer pointer','0x80029B68',32,
         ['EXE initialized word 0x80010000','0x80083DE4 LW','0x80083E38 LW'],
         'Separate native 0x758-byte temporary-state copies; not temporary flag bank'),
    ):
        add(key,'RAM / Native save staging',name,address,
            dict(address_space='PS1 virtual RAM / physical RAM',
                 native_access_width_bits=width,references=refs,note=note))
    for key,name,address,refs,note in (
        ('prepare','Save preparation source and size call site','0x80031B1C',
         ['0x80031B34 JAL 0x80060E14'],'Bounded call site; enclosing function recovery incomplete'),
        ('register','Native save source registration','0x80060E14',
         ['0x80031B34'],'Entry corroborated by call and preceding return; full behavior unresolved'),
        ('build','Native selected-slot card block builder','0x8006343C',
         ['0x80063718..0x80063814'],'Entry following previous return; selected bounded copy/CRC/write path traced'),
        ('copy','Native byte-copy loop','0x80084684',
         ['0x80063750 JAL 0x80084674'],'Loop site, not function entry'),
        ('crc','Native save block checksum','0x800638C0',
         ['0x800633E8','0x800637F4'],'Complete 28-word leaf body through return delay at 0x8006392C'),
        ('write','Native card write wrapper call site','0x8006015C',
         ['0x80063810 JAL 0x800600A8'],'0x2000 bytes passed to 0x800842AC; actual IO success untested'),
    ):
        add(key,'Code / Native save serialization',name,address,
            dict(address_space='PS1 virtual code / EXE offsets',references=refs,note=note,
                 native_sites=report['native_sites']))
    return entries
