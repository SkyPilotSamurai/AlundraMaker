"""Explicit native F-to-C handoff for a new fixed NPC, not retail replacement."""
import struct


def compile_fixed_npc_handoff(body):
    body = bytes(body)
    if not body or body[-1] != 255:
        raise ValueError('NPC continuation body must end with FF')
    # 66 copies global scratch to owner+234 and points its cursor at opcode+4.
    # 00 then yields the global F invocation; next native C runs owned context.
    return struct.pack('<BhB', 0x66, 4, 0) + body


def idle_tick_process(): return b'\xff'
