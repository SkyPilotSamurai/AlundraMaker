"""Bounded ordinary inventory increment through native opcode82.

Herb36 only pending independent gameplay checks for other types. No pickup,
obtained-item presentation, progressive normalization or capacity bypass.
"""
def compile_item_grant(item_id, quantity=1, obtained_message=None):
    """Native opcode 82 adds one of an item to the inventory (up to its
    maximum). Any item id; a quantity repeats it. Herb (36) is the audited
    case; other items use the same native call, not yet checked in game."""
    if type(item_id) is not int or not 0 <= item_id <= 255:
        raise ValueError('Give Item needs a native item from the database')
    if type(quantity) is not int or not 1 <= quantity <= 99:
        raise ValueError('Give Item quantity must be 1..99')
    if obtained_message:
        raise ValueError('Give Item has no automatic obtained-item message; add a Show Text command for it')
    return bytes((0x82, item_id)) * quantity


def grant_step(quantity, cap):
    """Bounded normal nonnegative native signed-halfword quantity/cap case."""
    if any(type(v) is not int or not 0 <= v <= 32767 for v in (quantity,cap)):
        raise ValueError('Normal quantity and cap must be nonnegative signed16')
    new=quantity if quantity==cap else quantity+1
    if new>32767:new-=65536
    return new,int(quantity<new)
