/* 80067A80: built-in program C101 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C101(struct Entity *e) {
    s32 sp10;
    s16 temp_v0_2;
    s16 temp_v1_3;
    s32 temp_a1;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_v0;
    s32 temp_v1;
    s32 temp_v1_4;
    s32 var_v0;
    s32 var_v0_2;
    u16 temp_v1_2;
    u32 temp_a1_2;

    if (e->bytes[1] == 0) {
        e->bytes[1] = 1;
        e->ai[4] = (s16) e->tile_x;
        e->ai[5] = (s16) e->tile_y;
        e->flags = (e->flags & ~0x2000) | 8;
    }
    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        temp_v1_2 = (u16) e->ai[1];
        temp_v1_3 = temp_v1_2 - 1;
        if (temp_v1_2 != 0) {
            e->ai[1] = temp_v1_3;
            if ((e->bytes[0] != 0) && ((temp_v1_3 & 0xFFFF) == 0x46) && !(g_mode_flags & 4)) {
                play_sound(0xCA);
                return;
            }
            return;
        }
        temp_a1 = (u16) e->ai[4] - e->tile_x;
        temp_v1_4 = (u16) e->ai[5] - e->tile_y;
        var_v0 = temp_a1;
        if (temp_a1 < 0) {
            var_v0 = -var_v0;
        }
        if (var_v0 < 8) {
            var_v0_2 = temp_v1_4;
            if (temp_v1_4 < 0) {
                var_v0_2 = -var_v0_2;
            }
            if (var_v0_2 >= 8) {
                goto block_19;
            }
            start_moving(e, 1, 0x12C, 0x14);
            return;
        }
block_19:
        e->target_anim = 1;
        temp_v0 = dir_from_delta(temp_a1 * 0x180000, temp_v1_4 << 0x14);
        temp_lo = g_rng_seed * 0x7D2B89DD;
        g_rng_seed = temp_lo + 0xE06A02E7;
        e->ai[1] = 0xF0;
        e->target_dir = (temp_v0 + (((temp_lo + 0xE06A02E7) / MULHI_9) - 4)) & 0x1F;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (temp_v0_2 & 0xFFFF) {
            if ((e->bytes[0] == 0) && (sp18 <= 0x200000)) {
                if ((sp10 < 3) && (sp14 < 3)) {
                    e->target_anim = 0;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->ai[1] = 0x50;
                    e->bytes[0] = 1;
                    return;
                }
                if ((sp10 < 5) && (sp14 < 5)) {
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    return;
                }
                goto block_30;
            }
block_30:
            if (e->force_adjusted != 0) {
                step_or_turn(e, 1, 3, 0x100000);
                return;
            }
            if ((ledge_turn(e, 1, 0x100000) == 0) && !((u16) e->ai[1] & 0x3F)) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                temp_a1_2 = temp_lo_2 + 0xE06A02E7;
                g_rng_seed = temp_a1_2;
                temp_lo_3 = temp_a1_2 * 0x7D2B89DD;
                if (((temp_lo_2 + 0xE06A02E7) / MULHI_3) == 0) {
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    e->target_dir = (e->target_dir + (((temp_lo_3 + 0xE06A02E7) / MULHI_9) - 4)) & 0x1F;
                    return;
                }
            }
        } else {
            e->target_anim = 0;
            e->ai[1] = 0x78;
            e->bytes[0] = 0;
            return;
        }
        break;
    case 5:
        if (e->on_ground != 0) {
            e->target_anim = 1;
        }
        break;
    }
}
