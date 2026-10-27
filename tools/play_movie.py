"""Play Movie event command (user 2026-10-27): end the game with one of the disc's movies.

The game cannot come back to play after a movie: the movie player is END.EXE, a separate
program. Static, stock US 1.1 (2026-10-27):
* ALUN_CD.EXE: a room change of type 9 (0x801F11F8) runs cdrom:\\END.EXE after the room loads
  (0x8002C70C `jal 0x8004AD18`, then LoadExec 0x800841DC). Change Map 0x53 keeps its Height byte
  as 0x801F1210 = height << 20.
* END.EXE: CdSearchFile(0x800FCA30, "\\MOVIE\\ARAN_END.MOV;1") at 0x800212CC; plays it with
  0x80023CC4(x 0, y 0x28, file, 0x19C5 frames, [sp+10] 0x800) at 0x8002131C; then LoadExec
  "cdrom:\\CLOSING.EXE;1" (the credits, 0x8002136C), which then starts the title (SLUS_005.53).
* SLUS_005.53 plays \\MOVIE\\USA_OP.MOV (x 0, y 0x28, 0xA4C frames) and \\MOVIE\\ARAN_OP.MOV
  (x 8, y 0x10, 0xEAB frames), both with 0x840 (0x800255C8..).

The command is Change Map to map 477 with type 9 and Height 0xF0 + movie. A stub on the type-9
path writes 'AMV' + movie to scratchpad 0x1F800200 (END.EXE uses only
scratchpad words 0 and 2; its stack at 0x801FFFF0 overwrote the first choice) before END.EXE
starts, or 0 for any other ending (the last map's own ending is unchanged). END.EXE gets a 2 KB
block in front (load address 0x8001F800) whose three stubs pick the file, the play settings and
the next program: the openings go to the title, the ending to the credits, Credits skips the
movie. Static only; needs an in-game check."""
import struct
from native_animation_spawns import _Asm, ZERO, A0, A1, A2, A3, V0, T0, T1, SP, RA, JR, BEQ, BNE, ADDIU, LW, SW, LUI

MOVIES = {'Opening logo': 0, 'Opening': 1, 'Ending (then credits)': 2, 'Credits': 3}
MOVIE_NAMES = {v: k for k, v in MOVIES.items()}
MAGIC, SELECT = 0x414D5600, 0x1F800200   # scratchpad: END.EXE's stack starts at 0x801FFFF0 (BizHawk 2026-10-27)
ALUN_HOOK, ALUN_WORD, ALUN_TARGET = 0x8002C70C, 0x0C012B46, 0x8004AD18
END_NAME, END_PLAY, END_EXEC = 0x800212CC, 0x8002131C, 0x8002136C
END_WORDS = {0x800212CC: 0x3C058002, 0x800212D0: 0x24A50000, 0x8002131C: 0x0C008F31, 0x8002136C: 0x3C048002, 0x80021370: 0x24840018}
END_PLAYER, END_FILE, END_TITLE, END_CLOSING = 0x80023CC4, 0x80020000, 0x800201FC, 0x80020018
ORI, SRL, SLTIU, LUI_OP = 13, 2, 11, 15


def compile_command(row):
    n = row.get('movie', 2)
    if n not in MOVIE_NAMES:
        raise ValueError('Play Movie: choose a movie')
    return bytes((0x53, 0xDD, 0x01, 0, 0, 0xF0 + n, 9, 0))


def used(document):
    def walk(rows):
        for r in rows or []:
            if isinstance(r, dict):
                if r.get('type') == 'play_movie':
                    return True
                for k in ('commands', 'then', 'else', 'branches', 'choices', 'body'):
                    v = r.get(k)
                    if isinstance(v, list) and walk(v):
                        return True
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and walk(item.get('commands')):
                                return True
        return False
    for g in (document or {}).get('event_graphs', []):
        for p in g.get('pages') or []:
            if walk(p.get('commands')) or any(walk(h.get('commands')) for h in p.get('trigger_actions') or []):
                return True
    return False


# -- ALUN_CD.EXE: remember the movie before END.EXE starts --------------------
def _alun_code(address):
    a = _Asm(address)
    a.li(T0, 0x801F1210); a.i(LW, T0, T0, 0); a.nop()
    a.r(SRL, rt=T0, rd=T0, shamt=20); a.i(12, T0, T0, 0xFF)             # height byte
    a.i(ADDIU, T0, T0, -0xF0); a.i(SLTIU, T0, T1, 4)
    a.branch(BEQ, T1, ZERO, 'plain'); a.r(0x21, rd=T1)                  # (t1 = 0 in the delay slot)
    a.li(T1, MAGIC); a.r(0x25, rs=T1, rt=T0, rd=T1)                     # or: 'AMV' + movie
    a.label('plain')
    a.li(T0, SELECT); a.i(SW, T0, T1, 0)
    a.j(2, ALUN_TARGET); a.nop()                                         # the game's own call
    return a.finish()


class AlunBlock:
    length = len(_alun_code(0x80010000))
    def __call__(self, address):
        return _alun_code(address)


def validate_alun(exe):
    load = struct.unpack_from('<I', exe, 0x18)[0]
    if struct.unpack_from('<I', exe, ALUN_HOOK - load + 0x800)[0] != ALUN_WORD:
        raise ValueError('Play Movie: the ending call at 0x8002C70C differs from the stock game')


def patch_alun(exe, address, offset_of):
    at = offset_of(exe, ALUN_HOOK)
    if struct.unpack_from('<I', exe, at)[0] != ALUN_WORD:
        raise ValueError('Play Movie: the ending call at 0x8002C70C differs from the stock game')
    struct.pack_into('<I', exe, at, 0x0C000000 | ((address >> 2) & 0x3FFFFFF))
    return dict(feature='play_movie', hook=hex(ALUN_HOOK), stub=hex(address))


# -- END.EXE: pick the movie, its settings and what comes next -----------------
def _end_code(base):
    """Three stubs + two file names at base. Returns (code, {stub: address})."""
    a = _Asm(base)
    def selected(reg):   # reg = movie, or -1 when none was asked for
        a.li(T0, SELECT); a.i(LW, T0, T0, 0); a.li(T1, 0xFFFFFF00); a.r(0x24, rs=T0, rt=T1, rd=T1)
        a.li(A3 if reg is None else reg, MAGIC)
    labels = {}
    # name: a1 = the file to look up
    a.label('name'); labels['name'] = a.here()
    a.li(T0, SELECT); a.i(LW, T0, T0, 0); a.li(T1, MAGIC + 0); a.nop()
    a.li(A1, END_FILE)
    a.branch(BEQ, T0, T1, 'n0'); a.i(ADDIU, T1, T1, 1)
    a.branch(BEQ, T0, T1, 'n1'); a.nop()
    a.r(JR, rs=RA); a.nop()
    a.label('n0'); a.li(A1, 0); a.fix_at = getattr(a, 'fix_at', []); a.fix_at.append(('usa', len(a.words) - 2))
    a.r(JR, rs=RA); a.nop()
    a.label('n1'); a.li(A1, 0); a.fix_at.append(('aran', len(a.words) - 2))
    a.r(JR, rs=RA); a.nop()
    # play: the movie's position, frames and buffer; Credits plays none
    a.label('play'); labels['play'] = a.here()
    a.li(T0, SELECT); a.i(LW, T0, T0, 0); a.li(T1, MAGIC + 0); a.nop()
    a.branch(BEQ, T0, T1, 'p0'); a.i(ADDIU, T1, T1, 1)
    a.branch(BEQ, T0, T1, 'p1'); a.i(ADDIU, T1, T1, 2)
    a.branch(BEQ, T0, T1, 'p3'); a.nop()
    a.j(2, END_PLAYER); a.nop()                                          # the ending, as the game plays it
    a.label('p0'); a.i(ADDIU, ZERO, A0, 0); a.i(ADDIU, ZERO, A1, 0x28); a.i(ADDIU, ZERO, A3, 0xA4C)
    a.branch(BEQ, ZERO, ZERO, 'pgo'); a.nop()
    a.label('p1'); a.i(ADDIU, ZERO, A0, 8); a.i(ADDIU, ZERO, A1, 0x10); a.i(ADDIU, ZERO, A3, 0xEAB)
    a.label('pgo'); a.i(ADDIU, ZERO, T1, 0x840); a.i(SW, SP, T1, 0x10)
    a.j(2, END_PLAYER); a.nop()
    a.label('p3'); a.r(JR, rs=RA); a.nop()                               # Credits: no movie
    # exec: a0 = the next program (openings: the title; ending / credits: the credits), forget the choice
    a.label('exec'); labels['exec'] = a.here()
    a.li(T0, SELECT); a.i(LW, T0, T0, 0); a.li(T1, MAGIC + 0); a.nop()
    a.li(A0, END_CLOSING)
    a.branch(BEQ, T0, T1, 'title'); a.i(ADDIU, T1, T1, 1)
    a.branch(BNE, T0, T1, 'forget'); a.nop()
    a.label('title'); a.li(A0, END_TITLE)
    a.label('forget'); a.li(T0, SELECT); a.i(SW, T0, ZERO, 0)
    a.r(JR, rs=RA); a.nop()
    code = bytearray(a.finish())
    names = {}
    for key, text in (('usa', b'\\MOVIE\\USA_OP.MOV;1\0'), ('aran', b'\\MOVIE\\ARAN_OP.MOV;1\0')):
        while len(code) % 4: code.append(0)
        names[key] = base + len(code); code += text
    for key, index in a.fix_at:   # li a1, name: lui + ori
        v = names[key]
        struct.pack_into('<I', code, 4 * index, (LUI_OP << 26) | (A1 << 16) | (v >> 16))
        struct.pack_into('<I', code, 4 * index + 4, (ORI << 26) | (A1 << 21) | (A1 << 16) | (v & 0xFFFF))
    return bytes(code), labels


def patch_end(end):
    end = bytes(end)
    load, size = struct.unpack_from('<II', end, 0x18)
    for address, word in END_WORDS.items():
        if struct.unpack_from('<I', end, address - load + 0x800)[0] != word:
            raise ValueError('Play Movie: END.EXE differs from the stock game')
    base = load - 0x800
    code, at = _end_code(base)
    if len(code) > 0x800:
        raise ValueError('Play Movie: END.EXE block too large')
    body = bytearray(end[0x800:])
    def put(address, word):
        struct.pack_into('<I', body, address - load, word)
    jal = lambda target: 0x0C000000 | ((target >> 2) & 0x3FFFFFF)
    put(END_NAME, jal(at['name'])); put(END_NAME + 4, 0)
    put(END_PLAY, jal(at['play']))
    put(END_EXEC, jal(at['exec'])); put(END_EXEC + 4, 0)
    header = bytearray(end[:0x800]); struct.pack_into('<II', header, 0x18, base, size + 0x800)
    return bytes(header) + code + bytes(0x800 - len(code)) + bytes(body)
