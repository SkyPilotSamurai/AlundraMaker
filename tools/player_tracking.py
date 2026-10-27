"""Track Player (enemies / bosses; on by default for Sara, user 2026-10-15).

Sara (C12, the demons' AI) only notices Alundra when he is in front of her: within
2 squares sideways and 4-5 ahead of the way she faces (0x80082E88). Until then she
idles and wanders in random directions, so from further away she rarely finds him.
This map program (B, whole map) turns her toward him while he is 3 or more tiles
away; her own AI still does everything else (her wandering then walks her his way,
and her sight check finds him):

  00              next frame
  43 T            work on the character (map template T); not there: wait
  04 back
  E9 03 FF        Alundra 3..255 tiles away (editor opcode, native_custom_ai)
  04 back         nearer: leave her alone
  27              face Alundra
  02 back
"""
import struct


def tracker(template, near=3):
    code = bytearray((0x00, 0x43, template, 0x04)) + struct.pack('<h', -3)
    code += bytes((0xE9, near, 0xFF, 0x04)) + struct.pack('<h', -9)
    code += bytes((0x27, 0x02)) + struct.pack('<h', -13) + bytes((0xFF,))
    return bytes(code)
