"""Check the generated event bytecode's native handler ABI in a target EXE.

This checks dispatch targets and handler signatures, not complete engine
equivalence or gameplay certification. File offsets come from each EXE header.
"""
import hashlib
import struct

STOCK_EXE_SHA256 = "12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3"
DISPATCH_TABLE_ADDRESS = 0x8009B814
SIGNATURE_BYTES = 128
SPRITE_CALLBACK_ROOTS = 0x8009B7B4


def _read_virtual(exe, address, length):
    if len(exe) < 2048 or exe[:8] != b"PS-X EXE":
        raise ValueError("Expected a PS-X EXE module")
    load, size = struct.unpack_from("<2I", exe, 0x18)
    if size > len(exe) - 2048 or not load <= address <= load + size - length:
        raise ValueError("Native event address is outside this EXE payload")
    offset = 2048 + address - load
    return bytes(exe[offset:offset + length])


def verify_event_vm_abi(candidate, stock, opcodes, private_state_manifest=None):
    """Reject a changed handler ABI for the actual opcodes being exported.

    Modded executables are allowed when these relevant dispatch entries and
    128-byte signatures remain compatible. Unknown revisions/changed handlers
    need independent instruction recovery rather than a universal offset delta.
    """
    if hashlib.sha256(stock).hexdigest() != STOCK_EXE_SHA256:
        raise ValueError("Native event reference executable does not match the verified local build")
    from project_state_runtime import OPCODES, verify_private_state_injection
    private_report=verify_private_state_injection(candidate,private_state_manifest) if private_state_manifest is not None else None
    rows = []
    dependencies = []
    for opcode in sorted(set(opcodes)):
        if type(opcode) is not int or not 0 <= opcode <= 255:
            raise ValueError("Event opcode outside native byte range")
        if opcode in OPCODES or opcode in (0xEA,0xEB,0xF0,0xF1,0xF2) or (opcode==0xE5 and private_state_manifest is not None and 'enemy_hp_zero' in private_state_manifest.get('optional_features',[])) or (opcode in (0xE6,0xE7) and private_state_manifest is not None and 'actor_route_resume' in private_state_manifest.get('optional_features',[])) or (opcode==0xE8 and private_state_manifest is not None and 'carryable_e2' in private_state_manifest.get('optional_features',[])) or (opcode in (0xE9,0xEC,0xED,0xEE) and private_state_manifest is not None and 'custom_ai' in private_state_manifest.get('optional_features',[])) or (opcode==0xEF and private_state_manifest is not None and 'hit_follow' in private_state_manifest.get('optional_features',[])):
            if private_report is None:raise ValueError('Private project state command requires its generated executable and manifest')
            entry=private_state_manifest['handlers'][str(opcode)]
            rows.append({'opcode':f'0x{opcode:02X}','signature_addresses':[hex(entry['address'])],'injected':True})
            continue
        if opcode == 255:
            # FF is also special-cased before dispatch: comparison at42E20
            # branches to42EB8 common yield/cleanup, never the table'sFF slot.
            addresses = [0x80042E1C, 0x80042EB8]
        elif opcode == 0:
            # Yield is handled directly by the dispatcher before table lookup.
            addresses = [0x80042E28, 0x80042D58]
        else:
            address = DISPATCH_TABLE_ADDRESS + opcode * 4
            expected = _read_virtual(stock, address, 4)
            if _read_virtual(candidate, address, 4) != expected:
                raise ValueError(f"Native event command{opcode:02X} dispatch target was changed in this game")
            addresses = [struct.unpack("<I", expected)[0]]
        for address in addresses:
            if _read_virtual(candidate, address, SIGNATURE_BYTES) != _read_virtual(stock, address, SIGNATURE_BYTES):
                raise ValueError(f"Native event command{opcode:02X} handler signature was changed in this game")
        rows.append({"opcode": f"0x{opcode:02X}", "signature_addresses": [hex(a) for a in addresses]})
        if opcode == 0x82:
            # Herb36 only: direct-grant dispatcher, default jump entry,
            # quantity getter, native signed-halfword increment/cap semantics.
            for start, length in ((0x80034814, 0x134), (0x80023234 + 36 * 4, 4),
                                  (0x800345DC, 0x38), (0x8004FAC4, 0x64),
                                  (0x8004FBE4, 0x9C)):
                if _read_virtual(candidate, start, length) != _read_virtual(stock, start, length):
                    raise ValueError('Native direct item grant dependency was changed in this game; progressive or custom grant semantics require independent validation')
                dependencies.append({'opcode': '0x82', 'address': hex(start), 'bytes': length})
    return {"module": "ALUN_CD.EXE", "relevant_handler_signatures_compatible": True,
            "signature_bytes": SIGNATURE_BYTES, "commands": rows, "dependencies": dependencies, "private_state": private_report, "gameplay_verified": False}


def verify_sprite_callback_abi(candidate, stock, callbacks, patched=()):
    """Check selected native sprite A/C/D/E/F callback dispatch and entry bytes.

    Root corroborated by native80039200..80039228: bank-indexed root LW,
    callback-indexed LW, null check and JALR. Does not prove whole callees.
    """
    if hashlib.sha256(stock).hexdigest() != STOCK_EXE_SHA256:
        raise ValueError('Sprite callback reference executable does not match the verified local build')
    rows = []
    selected = sorted(set(tuple(row) for row in callbacks))
    if selected and _read_virtual(candidate, 0x800391FC, 48) != _read_virtual(stock, 0x800391FC, 48):
        raise ValueError('Native sprite callback shared dispatch instructions changed')
    for bank, index in selected:
        if bank not in 'ACDEF' or type(index) is not int or not 0 <= index <= 255:
            raise ValueError('Native sprite callback must name bankA/C/D/E/F and index0..255')
        root_address = SPRITE_CALLBACK_ROOTS + 'ABCDEF'.index(bank)*4
        root = _read_virtual(stock, root_address, 4)
        if _read_virtual(candidate, root_address, 4) != root:
            raise ValueError(f'Native sprite callback bank{bank} dispatch root changed')
        table = struct.unpack('<I', root)[0]
        entry = table + index*4
        expected = _read_virtual(stock, entry, 4)
        if _read_virtual(candidate, entry, 4) != expected:
            raise ValueError(f'Native sprite callback{bank}{index:02X} dispatch target changed')
        address = struct.unpack('<I', expected)[0]
        # words the boss-points injection patched on purpose (patched site and its delay slot) are not compared
        mask = lambda raw: bytes(b if (address + k) & ~3 not in skip else 0 for k, b in enumerate(raw))
        skip = {a for site in patched for a in (site, site + 4)}
        if address and mask(_read_virtual(candidate, address, SIGNATURE_BYTES)) != mask(_read_virtual(stock, address, SIGNATURE_BYTES)):
            raise ValueError(f'Native sprite callback{bank}{index:02X} entry signature changed')
        rows.append({'bank': bank, 'index': index, 'handler_address': hex(address), 'null_handler': address == 0})
    return {'module': 'ALUN_CD.EXE', 'callback_entry_signatures_compatible': True,
            'signature_bytes': SIGNATURE_BYTES, 'shared_dispatch_bytes': 48,
            'callbacks': rows, 'gameplay_verified': False}


def sprite_callbacks(data, map_id, catalogue):
    """Read concrete class callback selectors from its actual selected bank."""
    if type(catalogue) is not int or not 0 <= catalogue <= 511:
        raise ValueError('Native sprite catalogue outside two banks')
    if catalogue < 256:
        start, end = struct.unpack_from('<2I', data)
    else:
        from map_block_repack import pointers, sections
        pp = pointers(data); base = pp[map_id]; h = sections(data[base:pp[map_id+1]])
        start, end = base+h[3], base+h[4]
    if not 0 <= start < start+48 <= end <= len(data):
        raise ValueError('Sprite callback bank bounds invalid')
    header = struct.unpack_from('<12I', data, start)
    table, stop = header[3:5]; index = catalogue & 255
    if not 48 <= table <= stop <= end-start or (stop-table)%4 or index >= (stop-table)//4:
        raise ValueError('Sprite callback table bounds invalid')
    pointer = struct.unpack_from('<i', data, start+table+index*4)[0]
    if not 48 <= pointer <= end-start-32:
        raise ValueError('Sprite callback header missing')
    return [(bank, data[start+pointer+19+i]) for i, bank in enumerate('ACDEF')]
