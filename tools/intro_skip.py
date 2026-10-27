"""Guarded normal-story intro skip using the stock first-wake completion tail.

No randomizer flag presets or map-variant overrides. Static validation only.
Original persistent flag0000 branch and all completion commands are preserved.
"""
import hashlib
import struct
from alundra_memory import parse_exe
from event_editor import instructions

ARRIVAL = dict(map_id=163, x=40, y=9, z=2)
EXE_FIELDS = (
    (0x80031D4C, 0x24120021, 0x24120028, 'player X'),
    (0x80031D50, 0x24130023, 0x24130009, 'player Y'),
    (0x80031D54, 0x0000A021, 0x24140002, 'player Z'),
    (0x80031D58, 0x24020185, 0x240200A3, 'new-game map'),
    (0x80031D64, 0x24020021, 0x24020028, 'saved camera X'),
    (0x80031D70, 0x2402003B, 0x24020009, 'saved camera Y'),
    (0x80031D80, 0xAC20D330, 0xAC34D330, 'saved camera Z'),
)
RETAINED_SETUP = bytes.fromhex('a6002d00')
FIRST_WAKE_BODY = bytes.fromhex('59000b106481c00398002400')
COMPLETION_TAIL = bytes.fromhex('0500001106c80005c900057e0600ff')


def intro_process_plan(session):
    """Return a fixed-size patch, rejecting an altered first-wake process."""
    rows = instructions(session, 163, 'B 1')
    if not rows or rows[-1][1] != 255:
        raise ValueError('First-wake B1 must decode through End process')
    start = rows[0][0]; end = rows[-1][0]
    branch = bytes(session.data[start:start+5])
    if branch[:3] != bytes.fromhex('300000') or start + struct.unpack_from('<h', branch, 3)[0] != end:
        raise ValueError('Original first-wake flag0000 completion guard changed')
    tail_start = end + 1 - len(COMPLETION_TAIL)
    if bytes(session.data[tail_start:end+1]) != COMPLETION_TAIL:
        raise ValueError('Original first-wake completion flags changed')
    if bytes(session.data[start+5:start+9]) != RETAINED_SETUP:
        raise ValueError('Original Jess spawn/music commands changed')
    offset = start + 9
    before = bytes(session.data[offset:offset+len(FIRST_WAKE_BODY)])
    # Search81 targets the real player; B/map logic is not the player itself.
    # Preserve the Jess spawn and BGM load, skip only cinematic setup/actions.
    after = b'\x59\x81\x00\x02' + struct.pack('<h', tail_start-(offset+3)) + bytes(6)
    if before not in (FIRST_WAKE_BODY, after):
        raise ValueError('Original first-wake setup commands changed')
    report = dict(map_id=163, bank='B', root_index=1,
        process_file_offset=hex(start), patch_file_offset=hex(offset),
        completion_file_offset=hex(tail_start), original_flag_guard_preserved=True,
        persistent_flags_set=[0x0000,0x00c9,0x067e],
        persistent_flags_cleared=[0x00c8], mass_progression_flags=False,
        native_animation_id=0, jess_spawn_and_music_preserved=True,
        before_hex=before.hex(), after_hex=after.hex())
    return offset, before, after, report


def patch_intro_spawn(exe):
    """Patch native new-game immediates with exact instruction preimages."""
    info = parse_exe(exe); data = bytearray(exe); sites=[]
    for address, old, new, label in EXE_FIELDS:
        offset = 0x800 + address-info['load_address']
        if not 0x800 <= offset <= 0x800+info['load_size']-4:
            raise ValueError('Intro spawn code outside executable payload')
        found = struct.unpack_from('<I', data, offset)[0]
        if found not in (old,new):
            raise ValueError(f'Intro spawn instruction changed at {address:08X}: {label}')
        sites.append(dict(native_address=hex(address), file_offset=hex(offset),
            field=label, before_word=f'{found:08x}', after_word=f'{new:08x}'))
    for site in sites:
        struct.pack_into('<I', data, int(site['file_offset'],16), int(site['after_word'],16))
    return bytes(data), sites


def apply_intro_skip(exe, session, *, patch_spawn=True):
    """Return (patched EXE, report) and apply one undoable DATAS edit.

    All preimages are validated before either result is accepted. Original
    inputs stay untouched; the caller exports to an independent game copy.
    """
    offset,before,after,process = intro_process_plan(session)
    if patch_spawn:
        patched,sites = patch_intro_spawn(exe)
    else:
        patched,sites = bytes(exe),[]
    if before != after:
        session.replace(offset,after,'Skip opening: retain first-wake completion flags')
    return patched,dict(format='alundra-normal-story-intro-skip-v1',
        spawn=ARRIVAL.copy() if patch_spawn else None, process=process, executable_sites=sites,
        spawn_fields_patched=patch_spawn,
        original_exe_sha256=hashlib.sha256(exe).hexdigest(),
        result_exe_sha256=hashlib.sha256(patched).hexdigest(),
        gameplay_verified=False, hardware_verified=False,
        source='Stock Beach416 C1 arrival + Jess first-wake163 B1 tail',
        limitation='Static entry tile and script validation; new-game control/story progression not emulator-tested')
