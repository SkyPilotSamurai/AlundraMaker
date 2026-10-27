"""Bounded new fixed-NPC F-to-C walking controller experiment.

The native distance wait must live in the actor-owned C context. This does
not authorize replacing arbitrary object AI, repeat routes or shared speeds.
"""
from event_movement_compile import compile_movement_command
from native_npc_continuation import compile_fixed_npc_handoff

# Each identity has a real cold-boot blocked/resumed four-direction route.
# This is not an inference that all NPCs share the same animation convention.
# 2026-10-22: further classes passed the same cold-boot route proof;
# see docs/2026-10-22-move-character-classes.txt.
VERIFIED_FIXED_NPC_ROUTE_CLASSES = frozenset((
    0, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 302, 349, 354, 355, 358, 359, 379, 399, 400, 434))


def fixed_route_load_process(catalogue):
    # Dog stock graphic omits collision bit80. An authored interaction route
    # needs collision selection; set only this new actor through native62.
    return bytes.fromhex('62808000ff') if catalogue == 289 else None


def compile_route_profile(data, catalogue, command, *, map_id, after=b''):
    route = compile_movement_command(data, catalogue, command, map_id=map_id)
    after = bytes(after)
    # Fixed NPC idle tick; F explicitly hands its remaining cursor to C.
    # The route ends at its native zero-speed idle animation before actions.
    body = route + after + b'\xff'
    return {'C': b'\xff', 'F': compile_fixed_npc_handoff(body)}, {
        'kind': 'new-fixed-npc-owned-route', 'catalogue': catalogue,
        'source': 'native F opcode66 transfers cursor/context to owned C',
        'blocked_behavior': command.get('blocked_behavior', 'wait'),
        'moving_animation': command['moving_animation'],
        'idle_animation': command['idle_animation'],
        'speed_percent': command.get('movement_speed', 100),
        'limits': ['New fixed NPC only', 'Native shared movement speed only',
                   'Physical touch interruption requires runtime validation',
                   'No repeated/default route or arbitrary-object AI replacement'],
        'runtime_verified': False,
    }
