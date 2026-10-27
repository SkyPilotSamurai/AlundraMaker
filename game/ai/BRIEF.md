# Built-in sprite AI port — brief for each porter

Goal: a **faithful, instruction-exact** Python port of every built-in sprite program (the A/C/D/E/F
"AI" functions the sprite headers name) of the US ALUN_CD.EXE (SLUS-00553), verified against the
original code running in a MIPS interpreter on RAM snapshots of the recompiled game.
The remake must eventually behave *exactly* like the game, frame for frame and RNG draw for RNG draw.
Paths below are relative to the decomp folder; on the linked computer it is
`"$HOME/mnt/Alundra Decomp"` (use `device_bash`; python3 + capstone + m2c are installed there).

## Your material
* `research/us_decomp/ai/GROUPS.txt` — your group's function list (address, size, which programs use it, callees).
* `research/us_decomp/ai/<ADDR>_<programs>.c` — m2c decompilation of each function, with the remake's
  field names (`e->target_anim`, `e->ai[1]`, `e->bytes[3]` ...). m2c is a guide, **the asm is the truth**:
  `python3 tools/us_decomp/fn.py 0xADDR` prints the whole function (jump tables included).
  `python3 tools/us_decomp/decomp.py 0xADDR` re-runs m2c (e.g. for a callee).
  m2c conventions here: `x / MULHI_61` means `hi(x * 61)` (multu+mfhi: the game's rnd(61) when x is the new seed);
  `D_80028AD8` etc. are EXE tables (read them with `g.mem.u8(0x80028AD8 + i)`); `rel_tile(e, &sp10)` fills
  sp10..sp24 = |dx| |dy| |dz| dx dy dz (the port returns that list); `M2C_ERROR(... stack arg ...)` = an
  argument passed on the stack: read the asm (`sw $x, 0x10($sp)` before the jal = 5th argument).
* `research/us_decomp/ai/MAPS.txt` — which maps place entities using each program (context only).
* `remake/engine/layout.py` — Entity record names/offsets (0x294 bytes), effect record (0x80 bytes), globals.
* `remake/engine/aihelp.py`, `remake/engine/ai_pilot.py` (C1 = the reference example), `remake/engine/entity.py`,
  `remake/engine/core.py`, `remake/engine/player.py` — ported helpers you call.

## Deliverable
1. `remake/engine/ai_g<N>.py` (N = your group number): one Python function per game function:
   ```python
   from .registry import port
   from .core import s32, s16, next_seed, hi
   from . import aihelp, core, entity, player, calls

   @port(0x8006821C)
   def ai_c1(g, e):            # name: ai_<first program that uses it>, lower case: ai_c1, ai_d21, ai_e3, ai_a12...
       """One line saying what it does in game terms (who uses it, what it makes the entity do)."""
   ```
   Local helpers that only your functions call (listed under `calls=` and not ported) go in the same file,
   also with `@port(ADDR)` (and `ret=True` if the return value is used, `ret='ptr'` for an entity/effect pointer).
2. `research/us_decomp/ai/REPORT_g<N>.md`: per function: address, programs, one-line behaviour, check result
   (`n/n match`, coverage), and anything unported it calls (address, arguments, what it does).
**Do not edit any other file** (shared engine files, the remake, the tools). If you find a bug in a shared
helper or the harness, write it in your report (with evidence) and work around it only by calling
`calls.call(g, ADDR, ...)` for that callee.

## Conventions (follow exactly)
* `g` = the game state; `e` = the entity (attributes named as in layout.py: `e.target_anim`, `e.px` (16.16),
  `e.flags`, `e.estatus` (Entity+0x10), `e.holder` (+0x28), `e.touching` (+0x224), `e.balance_addr` (+0x1C4) ...;
  unnamed words are `e.f_0FC` style (see layout.ENTITY)). `e.bytes[0..3]` = u8 at +0x274..+0x277,
  `e.ai[0..9]` = s16 at +0x280..+0x292 (both wrap automatically when stored; `e.ai[k]` READS signed like `lh`,
  use `e.ai[k] & 0xFFFF` where the game uses `lhu`). `e.slot` = slot number.
  A word load/store spanning them (m2c `e->unk274`, `lw 0x274`) = the four bytes little-endian
  (`b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24`; a word store sets all four); `lw 0x280` = `(ai[0] & 0xFFFF) | ai[1] << 16`.
  Some programs keep other things in generic fields (e.g. an entity ADDRESS in `e.delay`): store the int address
  (`entity.ent_addr(t)`) and read through it with `entity.ent_at(g, e.delay)`.
* Entity/effect pointer fields hold objects (`e.parent`, `e.riding`, `e.touching`, `e.shadow` ...) or None;
  compare with `is`. `g.ent[i]` = entity in slot i (0 = Alundra), `g.ent_count` (0x801D93EC), `g.fx[i]` = effect records.
  Address <-> object: `entity.ent_addr(e)`, `entity.ent_at(g, addr)`.
* Named globals are attributes: `g.rng_seed`, `g.mode_flags`, `g.pad_held` ... (layout.GLOBALS).
  **Everything else in memory** (EXE tables, sprite headers / animation data behind `e.header_addr`,
  balance records behind `e.balance_addr`, map info, unnamed globals) goes through `g.mem`:
  `g.mem.u8/s8/u16/s16/u32/s32(addr)` and `g.mem.w8/w16/w32(addr, v)` — exactly the loads/stores the game does
  (g.mem refuses addresses of the entity/effect tables and named globals: use the objects/attributes there).
* Integers: Python ints do not wrap. Wrap like the MIPS: `s32()` after any add/sub/mul whose result is stored
  or compared signed and can overflow; unsigned compares (`sltu`, `sltiu`, `bgeu`-style) need `& 0xFFFFFFFF`
  on both sides; `sra` = `>>` on an s32 value; `srl` = `(x & 0xFFFFFFFF) >> n`; `mult` low = `s32(a * b)`;
  `multu`+`mfhi` = `hi(a, b)`; `div` truncates toward zero (`int(a / b)` is wrong for big values: use
  `q = abs(a) // abs(b); q = -q if (a < 0) != (b < 0) else q`). Stores to s16/u8 fields wrap by themselves.
  Jump tables: `sltiu v0, v1, N` bounds an UNSIGNED switch (negative values go to default).
* Random numbers: `s = core.next_seed(g)` advances the game's seed (0x8009AF70) and returns it; `hi(s, n)` =
  rnd(n); `s >> 27`, `(s >> 19) & 0x7F` etc. as the asm does. Same number and order of draws as the game.
  Never use Python's random, floats, math.*, or any shortcut.
* Calls: the ported helpers (call them as module attributes so the checks can replay them):
  `aihelp.rel_tile(g, e)` -> list; `aihelp.rel_tile_z`, `aihelp.start_moving(g, e, anim, timer, chance)`,
  `aihelp.start_moving_half(g, e, anim, timer)`, `aihelp.ledge_turn(g, e, anim, drop)`, `aihelp.ledge_ahead(g, e, drop)`,
  `aihelp.sees_player(g, e, rel, near, far, zmax)`, `aihelp.sees_player_q(g, e, rel, q, near, far, zmax)`,
  `aihelp.near_in_front(g, e, rel, far, zmax)`, `aihelp.step_or_turn(g, e, anim_ok, anim_turn, climb)`,
  `aihelp.height_ahead(g, e, anim, d)`, `player.dir_from_delta(dx, dy)` (no g), `player.take_hit(g, e)`,
  `player.remove_entity(g, e)`, `player.break_blocks(g, e)`, `player.tile_height_above(g, e, ox, oy)`,
  `entity.spawn_warp_entity(g, parent, is_map, index, x, y, z, direction)` -> entity or None,
  `entity.destroy_entity(g, e, effect)`, `entity.select(g, logic, sel)` -> list (the game returns the count and
  leaves the list at 0x8013D488: use `len(...)` / the list), `entity.find_targets(g, e, mask, resp, ents_addr, dists_addr)`,
  `core.spawn_effect(g, bank_map, index, sub, x, y, z)` -> effect or None,
  `core.spawn_effect_on(g, bank_map, index, sub, ent, mode60, ox, oy, oz)`, `core.alloc_effect(g)`,
  `core.init_effect(...)`, `core.play_sound(g, n)`, `core.approach(v, target, step)`.
  Anything else not ported: `calls.call(g, 0xADDR, arg1, arg2, ...)` with exactly the arguments the game passes
  (stack arguments after the 4 register ones). In the checks the original's call is replayed (its stores and
  return value applied), so you can verify your function before its callees exist. Shared ones you will meet:
  0x80083394 (boss death puffs/flash, arg e), 0x800832B0 / 0x80083324 (screen flash/fade), 0x8004A7B4 (stop sound),
  0x8003AAE8 (spawn map record entity), 0x8003CA78 (map effect record). Replays cannot feed back data a callee
  writes into YOUR stack frame — if a callee fills a stack buffer you read, port that callee in your file.
* Keep the code close to the asm's structure (same order of side effects, same draws), but readable:
  short comments in game terms, no essays.

## Checking (mandatory for every function)
```
cd "$HOME/mnt/Alundra Decomp/tools/us_decomp"
timeout 170 python3 -u check_ai.py 0xADDR --snaps 'm9_5*' --fuzz 4
```
It runs the original and your port on every live entity of the chosen snapshots plus fuzzed copies
(target_anim, ai[], bytes[], hp, ground/wall/anim-done flags, Alundra next to it...), compares every field,
the RNG seed, the effect records and **every other byte of RAM**, and prints `n/n match` and the instruction
coverage of the original (`never ran` = paths no case reached). Snapshot sets (each 9-13 files):
`ship_*` `m9_*` `m13_*` `m50_*` `m82_*` `m92_*` `m141_*` (pattern e.g. 'm141_5*', 'm13_*').
Aim: all match on at least 3 different sets, and coverage of every reachable path. When the generic fuzz does not
reach a path (state kept in ai[3..9], parent/child links, timers...), write your own fuzz in
`tools/us_decomp/fuzz_g<N>.py` modelled on `ent_cases()` in check_ai.py (call `check.check(addr, snaps, fuzz=gen)`;
each variant is a function editing the RAM bytes, with `.label` and `.args_fn = lambda st: (st.ent[slot],)`).
The machine has 2 cores shared by several porters: keep runs small (one snapshot set, fuzz 3-4) while developing,
always prefix `timeout 170`, and run the wider confirmation once per function at the end.
A mismatch line names the field (`ent[5].target_dir: original 0x10 port 0x0`), `RAM 801F9460: ...` for g.mem bytes,
`... args [...] != original [...]` for a call made with different arguments, `the original called it N more time(s)`.

Do not start or stop the oracle (~/usbuild, port 4370) or touch ~/us; only read the snapshots through the tools.
Deleting files in the folder is not permitted (overwrite instead).

Report honestly: if something cannot be matched, say exactly what and why.
