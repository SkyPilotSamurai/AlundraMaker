"""Default English names for native music tracks and sound effects.

Source lists: data/upstream-music-names.csv and data/upstream-sound-names.csv,
copied unchanged from xcasadio/Alundra (MIT, commit 242b09a2; licence in
data/upstream-entity-names-LICENSE.txt). They are the JP debug name tables
with fan English translations. US localisation names are applied on top
(Anzes -> Jess, Muruta -> Murgg, ...). Names typed in the database always win.

Index mapping (checked against this workspace on 2026-10-07):
* music track t (map/event value) uses music list row t-1; track 0 = no music.
* sound effect ID n (event opcode 0x75 byte) uses sound list row n.
"""
import csv
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'
NO_MUSIC = 'No Music'
HIDDEN_TRACKS = {44}   # removed from the music lists (user 2026-10-18): 44 Warp (Unused)

US_MUSIC_NAMES = {
    'Alundra': 'Alundra', 'Anzes': 'Jess', 'Requiem?': 'Requiem', 'Giant deity': 'Giant Deity',
    'Final boss': 'Final Boss', 'Roein': 'Ronan', 'Muruta': 'Murgg', 'Nirude': 'Nirude',
    'Mom': 'Mother', 'End': 'Ending', 'Sektas': 'Septimus', 'Great tree': 'Casino',  # JP debug "great tree", but only the casino maps play it
    'Medium': 'Meia', 'Miming': 'Mimmings', 'Event clear': 'Event Clear',
    'Item obtained': 'Item Obtained',
}

# Whole-word US localisation fixes for the sound list (JP romanisation -> US release).
US_SOUND_WORDS = [
    (r'\bKing Muruta\b', 'Murgg'), (r'\bMuruta\b', 'Murgg'), (r'\bNilude\b', 'Nirude'),
    (r'\bKlein\b', 'Kline'), (r'\bIron ball:', 'Flail:'), (r'\bMimming\b', 'Mimmings'),
    (r'\bAnzes\b', 'Jess'), (r'\bRoein\b', 'Ronan'), (r'\bSektas\b', 'Septimus'),
    (r'\bZoldia\b', 'Zorgia'),   # US name (user 2026-10-22)
]
SOUND_FIXES = {3: 'Error', 78: 'Vibration (Alternate)',
               87: 'Monster Alundra', 88: 'Throw Back'}   # user names (2026-10-17)

# Official soundtrack titles. No US soundtrack album was released; these are the
# English titles of the Japanese "Alundra Original Game Soundtrack" (Antinos
# ARCJ-66, 1997) with US character/place names. Each was matched to a native
# track by the maps that play it (2026-10-07); tracks without a confident match
# keep their descriptive name. OST track number in the comment.
OST_TITLES = {
    1: 'Alundra',                              # 01
    16: 'The Village of Inoa',                 # 02  Inoa Village
    7: 'The Wind That Spans the Earth',        # 03  overworld field
    18: 'The House of Tarn',                   # 04  Tarn's Manor, Nava's Keep
    30: 'Nightmare',                           # 05  most dream dungeons
    6: 'Requiem',                              # 06  Lars Crypt
    21: 'The Coal Mine Where Devils Lurk',     # 07  Coal Mine, caves
    17: 'Tower of the Great Tree',             # 08  Great Tree
    22: 'Desert Temple',                       # 10  Ancient Shrine, Despair Desert
    31: 'Coastal Cave',                        # 11  Coastal Cave
    27: "Kline's Dream",                       # 12  Kline's Dream
    9: "The Lizardman's Lair",                 # 13  Reptile Lair, Lake Shrine outside
    32: "Meia's Past",                         # 14  (JP debug name: Medium/Meia)
    13: 'Nirude, the Forgotten God',           # 15  Nirude sector (JP debug: giant god)
    34: 'The Small Nation, Mimmings',          # 16  Nirude's Lair (Mimmings' home)
    35: 'Fairies of the River Bottom',         # 17  Fairy Pond
    11: 'Torla, the Mountain of Flame',        # 18  Torla Mountain
    15: 'The Mad Priest Ronan',                # 20  Ronan boss room
    23: 'The Holy Demon Shrine, Arisen',       # 21  Lake Shrine interior (final dungeon)
    33: 'Melzas',                              # Melzas boss room; album title unconfirmed (22 is the first boss theme per VGMO)
    14: 'Combined God Melzas',                 # 25  Melzas Brain boss room, the final fight
}


@lru_cache(maxsize=None)
def _english(filename):
    with (DATA / filename).open(encoding='utf-8-sig', newline='') as stream:
        return [(row.get('text_en') or '').strip() for row in csv.DictReader(stream, delimiter=';')]


def _cap(text):
    return text[:1].upper() + text[1:]


# Names chosen by the user (2026-10-09); they win over the soundtrack titles.
USER_TITLES = {1: 'Alundra, Opening Theme', 2: "Jess's Theme", 3: 'Stormy Seas', 12: 'Sanctuary',
    # Kohei's album names, except where the user kept the soundtrack title
    # (7, 11, 15, 16, 21, 30) or chose their own (6, 9, 24).
    4: 'Boss Battle I', 5: 'Boss Battle II', 41: 'Load Game', 6: "Lars's Crypt (Requiem)",
    8: 'Flaming Assault', 9: 'Reptile Lair', 10: 'Dust To Dust', 13: 'Nirude, The Giant God',
    17: 'Tower of the Great Tree', 18: "Tarn's Manor", 19: 'All Hail King Zazan',
    20: 'Man vs the gods', 22: 'Shifting Desert Sands', 23: 'Lake Shrine',
    24: "Septimus's Theme (Unused)", 25: 'Sail Away', 27: "Kline's Nightmare",
    28: 'Fairy Pond', 29: 'Gambling Fever', 31: 'Coastal Cave', 32: "Nestus's Dream",
    34: 'Inside Nirude', 35: "Meia's Dream",
    # Not loaded by any map, map script or known game code (2026-10-17 scan): marked Unused.
    # 46 named by the user.
    26: 'Temple (Unused)',
    37: 'Event Clear (Unused)',
    38: 'Event (Unused)',
    40: 'Item Obtained (Unused)',
    43: 'Death (Unused)',
    44: 'Warp (Unused)',
    36: 'Holy Sword',   # JP debug 'Clear': the Holy Sword get (user 2026-10-18)
    46: 'Sage II',
}

# Kohei's albums (map 143, Inoa: the composer's victrola, process C 4) play
# these native tracks in this order; titles are the in-game US text.
KOHEI_ALBUMS = {
    'Field of Dreams': [(1, 'Opening Theme'), (3, 'Stormy Seas'), (7, 'Wandering the Field'),
        (12, 'A Holy Place'), (16, 'In The Village'), (17, 'Tower of the Great Tree'),
        (22, 'Shifting Desert Sands'), (25, 'Sail Away')],
    'Serenade of Souls': [(2, 'Jess Arrives'), (6, 'Underground Tomb'), (10, 'Dust To Dust'),
        (18, "Tarn's Manor"), (21, "Workin' In A Coal Mine"), (30, 'Dream Dungeon'),
        (4, 'Boss Battle Part I'), (5, 'Boss Battle Part II')],
    'Dungeon Adventure': [(9, 'Lizardman Cave'), (13, 'Nirude, The Giant God'), (20, 'Man vs the gods'),
        (27, "Kline's Nightmare"), (29, 'Gambling Fever'), (31, 'Coastal Cave'), (34, 'Inside Nirude'),
        (35, "Meia's Dream")],
    'Dungeon Adventure II': [(8, 'Flaming Assault'), (11, 'Torla Mountain'), (15, 'Ronan Attacks!'),
        (19, 'All Hail King Zazan'), (23, 'Lake Shrine'), (28, 'Fairy Pond'), (32, "Nestus' Dream"),
        (24, 'Coming Soon!')],
}


def _every_word_capitalised(text):
    """'Man vs the gods' -> 'Man Vs The Gods'; the rest of each word is kept
    ("Lars's", '(Requiem)', 'II')."""
    def word(w):
        for i, ch in enumerate(w):
            if ch.isalpha():
                return w[:i] + ch.upper() + w[i + 1:]
        return w
    return ' '.join(word(w) for w in text.split(' '))


def music_default_name(track):
    if track == 0:
        return NO_MUSIC
    return _every_word_capitalised(_music_default_name(track))


def _music_default_name(track):
    if track in USER_TITLES:
        return USER_TITLES[track]
    if track in OST_TITLES:
        return OST_TITLES[track]
    names = _english('upstream-music-names.csv')
    raw = names[track - 1] if 0 < track <= len(names) else ''
    if not raw:
        return f'Unused Track {track}'
    return US_MUSIC_NAMES.get(raw, raw.title() if raw.islower() else _cap(raw))


@lru_cache(maxsize=None)
def _evidence_names():
    # data/sound-names.json: one name per sound with its evidence (record, sets, script maps,
    # PlaySound call sites); made by _claude_scripts/sound_name_gen_20261026.py
    import json
    try:
        return json.loads((DATA / 'sound-names.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def sound_default_name(sound_id):
    row = _evidence_names().get(str(sound_id))
    return row['name'] if row else upstream_sound_name(sound_id)


def upstream_sound_name(sound_id):
    if sound_id in SOUND_FIXES:
        return SOUND_FIXES[sound_id]
    names = _english('upstream-sound-names.csv')
    raw = names[sound_id] if 0 <= sound_id < len(names) else ''
    if not raw or raw.isdigit():
        return f'Unused Sound {sound_id}'
    for pattern, replacement in US_SOUND_WORDS:
        raw = re.sub(pattern, replacement, raw)
    # "12: on the eye plate" -> "12: On the eye plate"; "Sword: swing" -> "Sword: Swing"
    head, sep, tail = raw.partition(': ')
    return _cap(head) + (sep + _cap(tail) if sep else '')


def music_name(document, track):
    return document.get('music_names', {}).get(str(track)) or music_default_name(track)


def sound_name(document, sound_id):
    return document.get('sound_names', {}).get(str(sound_id)) or sound_default_name(sound_id)
