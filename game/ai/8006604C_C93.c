/* 8006604C: built-in program C93 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C93(struct Entity *e) {
    s32 sp10;
    s16 var_v0;
    s32 temp_a0;
    s32 temp_a1;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_t0;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_a0;
    s32 var_a1;
    s32 var_a1_2;
    s32 var_a2;
    s32 var_v0_2;
    u16 temp_v0;
    u8 temp_v0_2;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    if (temp_v1 < 0xA) {
        e->target_anim = 0xA;
        e->flags = (e->flags & ~0x80 & 0xFFF8FFFF) | 0x10000;
        e->item_state = e->py;
        e->delay = e->px;
        return;
    }
    if ((u32) (temp_v1 - 0xA) < 2U) {
        temp_v0 = (u16) e->ai[4];
        var_v0 = temp_v0 - 1;
        if (temp_v0 == 0) {
            if ((sp10 < 9) && (sp14 < 9) && !(g_mode_flags & 4)) {
                play_sound(0x192);
            }
            if ((u16) e->ai[5] != 0) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[5] = 0;
                var_v0 = ((temp_lo + 0xE06A02E7) / MULHI_61) + 0x64;
            } else {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->ai[5] = 1;
                var_v0 = ((temp_lo_2 + 0xE06A02E7) / MULHI_11) + 0xF;
            }
        }
        e->ai[4] = var_v0;
    }
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {                            /* irregular */
    case 10:
        if ((u16) e->ai[1] != 0) {
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            if ((((temp_lo_3 + 0xE06A02E7) / MULHI_5) == 0) && ((u32) ((u16) e->ai[1] - 0x32) < 0xBU) && (sp10 < 9) && (sp14 < 9)) {
                play_sound(0x192);
            }
            e->ai[1] = (u16) e->ai[1] - 1;
            if ((sp10 < 4) && (sp14 < 4) && (sp24 < 4)) {
                e->target_anim = 0xC;
                e->flags &= ~0x100;
                var_a0 = e->px - g_ent->px;
                var_a1 = e->py - g_ent->py;
                goto block_41;
            }
        } else {
            var_a1_2 = 0;
            e->target_anim = 0xB;
            if (e->bytes[0] != 0) {
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                var_a1_2 = (temp_lo_4 + 0xE06A02E7) / 1073741824;
            } else {
                temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_5 + 0xE06A02E7;
                e->bytes[0] = ((temp_lo_5 + 0xE06A02E7) / MULHI_3) + 3;
            }
            if (var_a1_2 == 0) {
                temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_6 + 0xE06A02E7;
                e->target_dir = (temp_lo_6 + 0xE06A02E7) / 134217728;
            }
            temp_t0 = e->px;
            temp_a0 = e->delay;
            temp_a3 = e->py;
            temp_a1 = e->item_state;
            var_v0_2 = temp_t0 - temp_a0;
            var_a2 = temp_a3 - temp_a1;
            if (var_v0_2 < 0) {
                var_v0_2 = -var_v0_2;
            }
            if (var_a2 < 0) {
                var_a2 = -var_a2;
            }
            if ((var_v0_2 > 0x8FFFFF) || (var_a2 > 0x5FFFFF)) {
                var_a0 = temp_a0 - temp_t0;
                var_a1 = temp_a1 - temp_a3;
block_41:
                e->target_dir = dir_from_delta(var_a0, var_a1);
                return;
            }
            return;
        }
        break;
    case 11:
        if (e->anim_done != 0) {
            e->target_anim = 0xA;
            temp_v0_2 = e->bytes[0] - 1;
            e->bytes[0] = temp_v0_2;
            if (temp_v0_2 & 0xFF) {
                e->ai[1] = 0x14;
                return;
            }
            e->ai[1] = 0x64;
            return;
        }
        break;
    case 12:
        if (e->pz > 0x03BFFFFF) {
            e->target_anim = 0xD;
            e->fz = 0;
            e->px = e->delay;
            e->py = e->item_state;
            return;
        }
        break;
    case 13:
        if (sp10 >= 0xE) {
            e->target_anim = 0xA;
            e->pz = 0;
            e->flags |= 0x100;
        }
        break;
    }
}
