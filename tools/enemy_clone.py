"""New enemies of their own (user 2026-10-11): a copy of an existing enemy,
boss or NPC that has its OWN class slot, so its HP, attacks, resistances and
behaviour are separate from the original even though it starts as a copy.

How it works in the game:
* Map-local class slots that no map of the original game uses and whose
  balance record is empty are free (scanned 2026-10-11 over maps 0-482 and
  BALANCE.BIN): FREE_SLOTS.
* BALANCE.BIN: the original's whole record chain (all tiers) is copied to the
  end of the file and the new slot's table entry points at it. The game loads
  BALANCE.BIN into a 0x3000-byte buffer (ALUN_CD.EXE 0x80045440: dest
  0x8012E3E8, size 0x3000), so the file may grow to 12288 bytes.
* DATAS.BIN: at build, the original's sprite (art, animations, hit boxes and
  its native AI callbacks, which are chosen by the sprite record, not by the
  slot number) is copied into the new slot on each map that places it.
Not yet tested in game: AIs that check their own slot number."""
import struct
from copy import deepcopy

FREE_SLOTS = (435, 436, 439, 442, 451, 457, 466, 331, 334, 352, 353)
BALANCE_LIMIT = 0x3000


def free_slot(definitions):
    taken = {r.get('source', {}).get('own_slot') for r in definitions}
    for slot in FREE_SLOTS:
        if slot not in taken:
            return slot
    raise ValueError(f'All {len(FREE_SLOTS)} free enemy slots are used')


def clone_balance(session, source_entry, target_entry):
    """Give target_entry its own copy of source_entry's record chain (undoable)."""
    from enemy_definition import BalanceTable
    data = bytes(session.data); table = BalanceTable(data)
    chain = table.chains[source_entry]
    last = chain[-1]; end = last + data[last + 1]
    raw = data[chain[0]:end]
    new_offset = len(data)
    if new_offset + len(raw) > BALANCE_LIMIT or new_offset > 0x7FFF:
        raise ValueError('BALANCE.BIN has no room for another enemy record')
    tail = data[len(session.original):] + raw
    session.set_tail(tail, 'New enemy record', ((target_entry * 2, struct.pack('<h', new_offset)),))
    BalanceTable(session.data)   # still valid
    return new_offset


def create_clone(editor, row, kind=None):
    if row.get('kind') not in ('enemy', 'boss', 'npc', 'object') or row.get('source', {}).get('catalogue_index') is None:
        raise ValueError('Choose an enemy, boss, NPC or object to copy')
    source = row['source']
    if source['catalogue_index'] < 256:
        raise ValueError('Only map-local classes can be copied as a new enemy for now')
    if type(source.get('balance_entry')) is not int:
        raise ValueError('This class has no balance record to copy')
    db = editor.database; slot = free_slot(db.definitions)
    balance = editor.native_balance_session()
    clone_balance(balance, source['balance_entry'], slot)
    new = db.new(kind or row['kind'], f"{row['name']} Copy")
    new['data'] = deepcopy(row.get('data', {}))
    new_source = deepcopy(source)
    new_source.update(own_slot=slot, balance_entry=slot, copied_from=row['id'])
    new['source'] = new_source
    editor.dirty = True
    register_previews([new])
    return new


def register_previews(definitions):
    """Previews of own-slot copies use their original's hand-picked pose."""
    import entity_preview
    for r in definitions:
        src = r.get('source', {})
        if type(src.get('own_slot')) is int:
            entity_preview.CLONE_BASE[src['own_slot']] = src.get('catalogue_index')
