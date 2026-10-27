"""NPC dialogue voices (user 2026-10-26).

The talk voice is chosen inside the text by a control code (remake/engine/message.py, message VM
0x80107568): \\B no voice, \\C..\\F voice 0..3 = game sound 0x4F + n (79..82), played on every
other letter, \\G no voice. The game's own dialogue gives each speaker a fixed voice; DEFAULTS is
the voice of the first control code of every Show Text (op 5C) whose speaker is that class, over
all original maps (scan of stock DATAS.BIN, 2026-10-26; one class used two: majority kept).
A class's 'dialogue_voice' (None = the game's default, 'none', or 0..3) overrides it."""

DEFAULTS = {25: 0, 256: 0, 257: 1, 258: 2, 259: 1, 260: 0, 261: 0, 262: 1, 263: 1, 265: 0, 267: 0,
            268: 0, 273: 0, 274: 0, 275: 1, 276: 1, 277: 0, 278: 2, 279: 2, 280: 0, 281: 1, 282: 0,
            283: 0, 284: 1, 285: 0, 287: 0, 288: 1, 302: 1, 339: 1, 347: 2, 349: 1, 354: 0, 356: 2,
            370: 'none', 377: 2, 378: 0, 379: 0, 386: 2, 399: 0, 400: 1, 402: 0, 412: 3, 417: 0,
            418: 3, 426: 3, 493: 3, 495: 3, 506: 3, 509: 3}
CHOICES = (('none', 'No voice'), (0, 'Voice 1 (sound 79)'), (1, 'Voice 2 (sound 80)'),
           (2, 'Voice 3 (sound 81)'), (3, 'Voice 4 (sound 82)'))


def default_voice(definition):
    return DEFAULTS.get(((definition or {}).get('source') or {}).get('catalogue_index'))


def voice_of(definition):
    """The voice a class speaks with: its own setting, else the game's default, else None."""
    chosen = ((definition or {}).get('data') or {}).get('dialogue_voice')
    return chosen if chosen is not None else default_voice(definition)


def apply(text, voice):
    """Text with the voice's control code in front, unless the text already sets a voice."""
    if voice is None or not isinstance(text, str) or text[:2] in ('\\B', '\\C', '\\D', '\\E', '\\F', '\\G'):
        return text
    return ('\\B' if voice == 'none' else '\\' + 'CDEF'[voice]) + text
