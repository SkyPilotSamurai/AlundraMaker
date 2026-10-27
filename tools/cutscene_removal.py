"""Remove Cutscenes mod option.

Skips story cutscenes the game can do without, keeping the normal story and
item order. Applied at Build to a copy of the game data; every change is
checked against the expected original bytes (stock US v1.1 script, found
through the map's script roots so other edits do not move it).

Sources: Dinopony's Alundra randomizer (MIT, copyright 2022 Dinopony;
docs/OPEN_WORLD_RANDOMIZER_LICENSE.txt), patch_remove_cutscenes.hpp and
patch_remove_items_fanfare.hpp, already pinned in
data/editor-open-world-recipe.json.

Removed:
* Dark Dragon: straight to the Melzas fight (no Sanctuary scene), HUD kept.
* Murggs running through the woods (Overworld A2).
* Watchtower scene (Overworld A1); the big rocks and villagers' scene that
  waited for it now wait for the Coal Mine boss instead, and the meatball
  rockfall no longer sets the flag that blocked the mine on re-entry.
* Villagers praying at the Magyscar entrance.
* Lars Crypt: the door opens when the master sage scene starts, so the five
  sages appearing one by one is skipped.
* Nirude: after the boss, straight back outside (broken Nirude variant).
* Item fanfare: rare chest items use the normal item pickup instead of the
  fanfare pause (ALUN_CD.EXE item table, byte 5: 0x00 -> 0x34).
* With it, the opening is skipped (as Skip intro).
Kept on purpose: the night after Wilda (Bergus is kidnapped; the story
continues from there) and every dream, boss intro and dialogue.
"""
import struct

SOURCE = 'patch_remove_cutscenes.hpp'
STORY_LINES_KEPT = {90, 94}   # post-Wilda night: needed by the normal story
ITEM_INFO_VA, ITEM_COUNT, FANFARE, COMMON = 0x800C7DE4, 0x5A, 0x00, 0x34  # randomizer ITEM_COUNT


def selected(row):
    return row['source_path'].endswith(SOURCE) and row['source_line'] not in STORY_LINES_KEPT


def cutscene_plan(session):
    from editor_open_world import world_access_plan
    plans, recipe = world_access_plan(session, selected)
    return plans, recipe


def apply_cutscene_removal(session):
    """Patch the build copy's DATAS. Returns a report."""
    plans, recipe = cutscene_plan(session)
    changes = []
    for offset, before, after, row in plans:
        if before != after:
            session.replace(offset, after, 'Remove cutscene: map ' + str(row['map_id']))
        changes.append(dict(map_id=row['map_id'], file_offset=hex(offset), before=before.hex(),
                            after=after.hex(), source_line=row['source_line']))
    return dict(format='alundra-editor-remove-cutscenes-v1', changes=changes,
                source_commit=recipe['source_commit'], kept_story_lines=sorted(STORY_LINES_KEPT),
                gameplay_verified=False)


def remove_item_fanfares(exe):
    """Rare items stop using the fanfare effect. Returns (exe, report)."""
    data = bytearray(exe)
    load, size = struct.unpack_from('<II', data, 0x18)
    base = ITEM_INFO_VA - load + 0x800
    if base < 0x800 or base + ITEM_COUNT * 8 > 0x800 + size:
        raise ValueError('Item table outside this executable')
    changed = []
    for item in range(ITEM_COUNT):
        o = base + item * 8 + 5
        if data[o] == FANFARE:
            data[o] = COMMON; changed.append(item)
    return bytes(data), dict(feature='remove_item_fanfares', items=changed, table_va=hex(ITEM_INFO_VA))
