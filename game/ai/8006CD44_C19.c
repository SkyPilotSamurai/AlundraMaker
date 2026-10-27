/* 8006CD44: built-in program C19 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C19(struct Entity *e) {
    s32 sp10;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    u16 temp_v0;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 == 0) {
            if (e->bytes[0] != 0) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->target_anim = 3;
block_25:
                e->bytes[0] = 0;
                return;
            }
            e->target_anim = 1;
            return;
        }
        e->ai[1] = temp_v0 - 1;
        return;
    case 1:
        if ((sp10 < 3) && (sp14 < 3) && (sp18 <= 0x100000)) {
            e->bytes[0] = 1;
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / 268435456) + 0x3C;
            return;
        }
        if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->ai[1] = 0x3C;
            e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
            return;
        }
        break;
    case 5:
        if (e->on_ground != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x14;
            play_sound(0x96);
            return;
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 0;
            e->ai[1] = 0x14;
            goto block_25;
        }
        break;
    }
}
