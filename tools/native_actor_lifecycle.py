"""Native actor presence helpers, not arbitrary conditional graphic swapping.

19/5D are deactivation (status3), not invisibility. True absence uses2E native
destruction; respawning2D starts the template's load callbacks again. Controller
must be a separate persistent map process with an active owner, never the actor
it is destroying. Source search for numeric InitData uses owner's status.
"""
import hashlib
import struct
from event_switch_registry import validate_native_flag_operand
from event_logic_compile import _Assembler

STOCK_EXE_SHA256 = '12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3'
HANDLERS = {0x19: 0x8003E220, 0x2C: 0x8003E704, 0x2D: 0x8003E744,
            0x2E: 0x8003E788, 0x5D: 0x8003FC14}


def _index(value):
    if type(value) is not int or not 0 <= value <= 127:
        raise ValueError('Owned native InitData index must be0..127')
    return value


def conditional_template(raw):
    """Copy a verified donor/template and suppress initial map auto-spawning.

    This preserves hook/collection semantics; caller independently validates
    them for the new actor. It deliberately does not erase a chest collection
    flag or stock event hook to pretend that it is a safe new object.
    """
    raw = bytes(raw)
    if len(raw) != 20 or raw[4] != 1 or raw[2:4] == b'\0\0':
        raise ValueError('Conditional actor needs a live20-byte native template')
    result = bytearray(raw)
    result[5] &= ~0x40
    return bytes(result)


def compile_destroy_owned_template(template_index):
    """2E numeric selector, exclusively for a caller-owned new template.

    Selection can match multiple spawned instances of that InitData identity;
    all are destroyed. Native cleanup is deferred, not a render-only toggle.
    """
    return bytes((0x2E, _index(template_index)))


def compile_switch_presence_watcher(native_flag_operand, template_index, *, when_set=True):
    """Continuous switch-driven spawn/despawn, bytes WITHOUT finalFF.

    Runs one00yield per poll. ON and absent ->2Dspawn;ON and present ->no-op.
    OFF and present ->2Edestroy;OFF and absent ->no-op. `when_set=False` inverts
    visibility. Starts no new event pages/portraits and changes no stock flags.
    Spawn resets HP/animation/callback state; pickup/collected chests need their
    own eligibility predicate or they will respawn. Runtime watcher scheduling,
    actor pool exhaustion and load callbacks must still be tested.
    """
    flag = validate_native_flag_operand(native_flag_operand)
    index = _index(template_index)
    if type(when_set) is not bool:
        raise ValueError('Presence condition must be boolean')
    asm = _Assembler()
    asm.label('poll')
    asm.data.append(0)
    asm.branch(0x31 if when_set else 0x30, 'hide', flag)
    asm.data.extend((0x2C, index))
    asm.branch(4, 'repeat')  # 2C is true exactly when no matching entity exists.
    asm.data.extend((0x2D, index))
    asm.branch(2, 'repeat')
    asm.label('hide')
    asm.data.extend((0x2C, index))
    asm.branch(3, 'repeat')
    asm.data.extend(compile_destroy_owned_template(index))
    asm.label('repeat')
    asm.branch(2, 'poll')
    return asm.finish()


def recover_native_evidence(exe):
    """Fingerprint-backed direct instruction observations, no gameplay claim."""
    exe = bytes(exe)
    if hashlib.sha256(exe).hexdigest() != STOCK_EXE_SHA256 or exe[:8] != b'PS-X EXE':
        raise ValueError('Lifecycle recovery requires fingerprinted stock module')
    load, size = struct.unpack_from('<II', exe, 0x18)

    def word(address):
        offset = address - load
        if not 0 <= offset <= size - 4 or 0x804 + offset > len(exe):
            raise ValueError('Instruction outside native payload')
        return struct.unpack_from('<I', exe, offset + 0x800)[0]

    for opcode, expected in HANDLERS.items():
        if word(0x8009B814 + opcode * 4) != expected:
            raise ValueError('Native lifecycle dispatch changed')
    ranges = [(0x8003E220, 0x8003E230), (0x8003E704, 0x8003E80C),
              (0x8003FC14, 0x8003FC70), (0x8003B0C8, 0x8003B104),
              (0x80038EB4, 0x80038F24), (0x80038F24, 0x80038FC4)]
    return {'module': 'stock ALUN_CD.EXE', 'sha256': STOCK_EXE_SHA256,
            'native_handlers': {f'{op:02X}': f'{addr:08X}' for op, addr in HANDLERS.items()},
            'instruction_ranges': [{'start': f'{a:08X}', 'end_exclusive': f'{z:08X}',
                                    'words': [f'{word(p):08X}' for p in range(a, z, 4)]}
                                   for a, z in ranges],
            'observations': ['19/5D set actor status3; not invisible',
                             'Native visible list includes statuses2/3 via unsigned(status-2)<2',
                             '2E searches selector and calls8003B0C8 storing status4',
                             'Native cleanup status4 copies reset template and retains slot index',
                             '2D spawns existing InitData with notCheckSpawnZone=1'],
            'runtime_verified': False,
            'limits': ['Controller must retain active owner and not destroy itself',
                       'Spawned actor load/AI hooks and collisions are unchanged',
                       'Respawn resets actor state; not persistent page-local state',
                       'Collected rewards need separate predicate; flag alone can respawn them']}


def compile_condition_presence_watcher(pages, template_index, once=None, blockers=()):
    """Spawn/despawn an owned actor from its event page conditions, bytes
    WITHOUT final FF. The actor is present while ANY page has ALL of its
    conditions true (RPG-style: no matching page, no event).

    `pages` is a list of condition lists; each condition is either
    ('flag', native_flag_operand, when_set) or ('test', bytes) where the bytes
    set the VM condition register (project switch/variable tests, E1/E4).
    """
    index = _index(template_index)
    if not pages or (any(not conditions for conditions in pages) and not blockers):
        raise ValueError('Every page needs at least one condition')
    asm = _Assembler()
    if once:   # spawn once per visit; vanishing afterwards = killed for good
        asm.data.extend(once['clear_spawned'])
        asm.data.extend(once.get('clear_killed', b''))
    asm.label('poll')
    asm.data.append(0)

    def page_tests(conditions, fail):
        for condition in conditions:
            if condition[0] == 'flag':
                flag = validate_native_flag_operand(condition[1])
                asm.branch(0x31 if condition[2] else 0x30, fail, flag)
            elif condition[0] == 'code':     # item / game tests: [(bytes, branch on failure)]
                for raw, fail_branch in condition[1]:
                    asm.data.extend(raw)
                    asm.branch(fail_branch, fail)
            elif condition[0] == 'test':
                asm.data.extend(condition[1])
                asm.branch(4, fail)          # condition false -> next page
            else:
                raise ValueError('Unknown presence condition')

    # A later page in force (all its conditions hold) hides this one (RPG-style: the
    # highest page whose conditions hold is the one in force), whatever its conditions are.
    for number, conditions in enumerate(blockers):
        if not conditions:
            raise ValueError('A later page with no conditions is always in force')
        page_tests(conditions, f'later{number + 1}')
        asm.branch(2, 'hide')
        asm.label(f'later{number + 1}')
    for number, conditions in enumerate(pages):
        fail = f'page{number + 1}'
        page_tests(conditions, fail)
        asm.branch(2, 'show')
        asm.label(fail)
    # No page matched: remove the actor if present.
    asm.label('hide')
    asm.data.extend((0x2C, index))
    asm.branch(3, 'repeat')
    asm.data.extend(compile_destroy_owned_template(index))
    if once:
        asm.data.extend(once['clear_spawned'])
    asm.branch(2, 'repeat')
    asm.label('show')
    asm.data.extend((0x2C, index))
    asm.branch(4, 'present' if once else 'repeat')   # 2C true exactly when no matching entity exists
    if once:
        asm.data.extend(once['spawned_test'])
        asm.branch(4, 'spawn')               # not spawned yet this visit
        asm.data.extend(once['set_killed'])  # it was here and is gone: killed
        asm.branch(2, 'repeat')
        asm.label('spawn')
        asm.data.extend(once['set_spawned'])
    asm.data.extend((0x2D, index))
    if once:
        # Present, whoever spawned it (the map itself at load, or this controller): it counts as
        # spawned this visit, so its disappearance is its death. Without this an actor the map
        # spawned at load was spawned again after its first death (user 2026-10-20).
        asm.branch(2, 'repeat')
        asm.label('present')
        asm.data.extend(once['set_spawned'])
    asm.label('repeat')
    asm.branch(2, 'poll')
    return asm.finish()
