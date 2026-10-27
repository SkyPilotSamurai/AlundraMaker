/* 80065F44: built-in program C92 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C92(struct Entity *e) {
    s32 sp10;
    s32 temp_lo;

    rel_tile(e, &sp10);
    if (e->target_anim == 0) {
        if ((sp10 < 4) && (sp14 < 4) && (sp24 <= 0)) {
            if (!(g_mode_flags & 4)) {
                play_sound(0x1D4);
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 1;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->target_dir = ((temp_lo + 0xE06A02E7) / MULHI_7) + 5;
        }
    } else if (e->pz > 0x03BFFFFF) {
        remove_entity(e);
    }
}
