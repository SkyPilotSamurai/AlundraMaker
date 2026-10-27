"""Relocate a bounded native object controller onto private instance switches.

Preserves native animation/yield/actor-bit instructions. This is a compiler
primitive, not permission to transplant arbitrary room scripts. Unsupported
opcodes and branch targets inside operands are rejected before allocation.
Private state currently survives map transitions, not executable/save reloads.
"""
import struct
from event_logic_compile import _Assembler
from project_state_runtime import compile_project_command, compile_project_condition

LENGTHS = {0x00:1, 0x02:3, 0x03:3, 0x04:3, 0x05:3, 0x06:3,
           0x1A:2, 0x1C:2, 0x2A:1, 0x2B:1, 0x30:5, 0x31:5,
           0x32:3, 0xFF:1}


def rebind_controller(code, flag_bindings, registry, *, insert_before=None):
    """Return code/report; bindings explicitly map native operands to IDs.

    No old map switch is retained. Both branches and toggle expansions use
    opcode-relative native displacements after resizing the instructions.
    """
    code = bytes(code)
    rows = []; offset = 0
    while offset < len(code):
        op = code[offset]; length = LENGTHS.get(op)
        if length is None:
            raise ValueError(f'Unrecovered object controller opcode {op:02X} at {offset}')
        if offset + length > len(code):
            raise ValueError('Truncated object controller instruction')
        rows.append((offset, op, code[offset:offset+length])); offset += length
    if not rows or rows[-1][1] != 0xFF:
        raise ValueError('Object controller needs an explicit final FF')
    boundaries = {pos for pos, _, _ in rows}
    insert_before = insert_before or {}
    if any(type(pos) is not int or pos not in boundaries for pos in insert_before):
        raise ValueError('Object continuation must attach at an instruction boundary')
    asm = _Assembler(); operands = set(); targets = []
    def state(operand, value, condition=False):
        if operand not in flag_bindings:
            raise ValueError(f'Unbound map-owned flag {operand:04X}')
        operands.add(operand)
        row = {'type':'switch' if condition else 'set_switch',
               'switch_scope':'project', 'switch_id':flag_bindings[operand], 'value':value}
        return (compile_project_condition if condition else compile_project_command)(row, registry)
    for pos, op, raw in rows:
        asm.label(('old', pos))
        # The caller owns compilation/ABI verification of authored commands.
        # Relocated incoming branches must include this continuation exactly once.
        asm.data.extend(insert_before.get(pos, b''))
        if op in (2, 3, 4, 0x30, 0x31):
            target = pos + struct.unpack_from('<h', raw, len(raw)-2)[0]
            if target not in boundaries:
                raise ValueError('Native controller branch targets an operand or leaves the program')
            targets.append({'source':pos, 'target':target})
            if op in (0x30, 0x31):
                operand = struct.unpack_from('<H', raw, 1)[0]
                asm.data.extend(state(operand, op == 0x30, True))
                asm.branch(3, ('old', target))
            else:
                asm.branch(op, ('old', target))
        elif op in (5, 6, 0x32):
            operand = struct.unpack_from('<H', raw, 1)[0]
            if op == 0x32:
                on = ('toggle-on', pos); end = ('toggle-end', pos)
                asm.data.extend(state(operand, True, True)); asm.branch(4, on)
                asm.data.extend(state(operand, False)); asm.branch(2, end)
                asm.label(on); asm.data.extend(state(operand, True)); asm.label(end)
            else:
                asm.data.extend(state(operand, op == 5))
        else:
            asm.data.extend(raw)
    result = asm.finish()
    return result, {'source_length':len(code), 'result_length':len(result),
                    'native_flags_replaced':sorted(operands), 'branches':targets,
                    'gameplay_verified':False, 'memory_card_persistent':False}
