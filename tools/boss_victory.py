"""Boss victory: what the game does when a boss is beaten (user 2026-10-15).

Every boss room of the game calls the same routine once the boss is gone
(`00 2C T 04 FD FF`: wait until no entity of template T is left) or, for Wilda
(map 325), once the boss code sets room flag 8000 (bit 0 of 801E6378):

  A6 01           stop the music, fading out
  37 8C 00        wait 140 frames (the fade; the delay before the fanfare)
  A7 2A 00        load music track 2A, the victory fanfare
  37 1E 00        wait 30 frames
  A8 03 FE FF 00  wait until it has loaded
  8D 81 04 FD FF  wait until Alundra stands on the ground
  10 A5           hold the player, stop the sounds
  5B 81 5B 00     Alundra: animation 5B (sword raised), facing down
  5C 81 TT 01     the text (mode 1: the world keeps running)
  50 04           the script closes the window
  37 F0 37 F0 37 C8 51 37 28 39   about 12 s, then close it and wait
  59 81 00        Alundra back to standing
  A7 00 00 00 A8 03 FE FF   unload the fanfare
  11              give the player control back

The text is the boss room's own ("\\B\\N\\HDefeated the Shrine Protector.").
"""
import gzip, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTINE = bytes.fromhex('a6 01 37 8c 00 a7 2a 00 37 1e 00 a8 03 fe ff')
DELAY = bytes.fromhex('37 8c 00')
VICTORY_FLAG = 0x8000
# Bosses whose own AI signals defeat with room flag 8000 and then stays where it fell (its home
# room's program made it leave): Melzas, C55 case 15 (research/us_decomp/ai/8007C32C_C55.c lines
# 289-294), 60 frames after its death animation. Placed elsewhere it is removed once the flag is set.
FLAG_AND_REMOVE_HOMES = {327: 'Melzas'}


def sequence(text_ref, delay=True):
    """The game's victory routine (without its return), text = map text reference."""
    code = bytes.fromhex('a6 01') + (DELAY if delay else bytes((0x00,)))
    code += bytes.fromhex('a7 2a 00 37 1e 00 a8 03 fe ff 00 8d 81 04 fd ff 10 a5 5b 81 5b 00')
    code += bytes((0x5C, 0x81, text_ref, 0x01))
    code += bytes.fromhex('50 04 37 f0 37 f0 37 c8 51 37 28 39 59 81 00 a7 00 00 00 a8 03 fe ff 11')
    return code


def markup(text):
    """The game's look for the victory line: no talk sound, one line down, centred."""
    text = (text or '').strip() or 'Defeated the boss.'
    return text if text.startswith('\\') else '\\B\\N\\H' + text


def _block(m, data=None):
    path = ROOT / f'game/object-library/maps/{m:03d}.blk.gz'
    try:
        return gzip.open(path).read()
    except OSError:
        if data is None:
            return None
        from map_block_repack import pointers
        o = pointers(data)
        return bytes(data[o[m]:o[m + 1]])


def home_victory(home, data=None):
    """(text or None, waits_for_flag) of the boss room `home` in the original game."""
    from map_block_repack import sections
    from native_script_allocation import script_tables
    if type(home) is not int or not 0 <= home < 483:
        return None, False
    if home in FLAG_AND_REMOVE_HOMES:
        return None, 'remove'
    block = _block(home, data)
    if block is None:
        return None, False
    so = sections(block)
    _, _, code, _ = script_tables(block[so[3]:so[4]])
    at = code.find(ROUTINE)
    if at < 0:
        return None, False
    flag = False
    for i in range(len(code) - 2):
        if code[i] == 0x78 and i + struct.unpack_from('<h', code, i + 1)[0] == at:
            flag = flag or bytes.fromhex('36 00 80') in code[max(0, i - 8):i]
    text = None
    m = code.find(bytes.fromhex('5b 81 5b 00'), at)
    if 0 <= m < at + 60:
        op = code[m + 4]
        ref = code[m + 6] if op == 0x5C else code[m + 5] if op == 0x0D else None
        if ref is not None and ref & 0x80:
            start = so[6]
            value = struct.unpack_from('<h', block, start + 2 * (ref & 0x7F))[0]
            if value > 0:
                end = block.find(0, start + value)
                text = block[start + value:end].decode('latin-1')
    return text, flag


def watcher(bosses, text_ref, after=b''):
    """Map program (B, whole map): wait until every boss has come, then until each is
    beaten (gone, or room flag 8000 for those whose room waits for it), then the
    victory; afterwards it idles, so it plays once per visit.
    bosses: [(template index, waits_for_flag)]."""
    code = bytearray()
    for template, _ in bosses:
        code += bytes((0x00, 0x2C, template, 0x03, 0xFD, 0xFF))   # until it is there
    for template, flag in bosses:
        if flag:
            code += bytes((0x00, 0x30)) + struct.pack('<Hh', VICTORY_FLAG, 10) + bytes((0x2C, template, 0x04)) + struct.pack('<h', -8)
            if flag == 'remove':
                code += bytes((0x2E, template))   # remove characters: the boss that stayed where it fell
        else:
            code += bytes((0x00, 0x2C, template, 0x04, 0xFD, 0xFF))   # until it is gone
    code += sequence(text_ref, delay=True)
    code += after   # the bosses' death actions, once the victory text is closed (user 2026-10-27)
    code += bytes((0x00, 0x02, 0xFF, 0xFF, 0xFF))
    return bytes(code)
