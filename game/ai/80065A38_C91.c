/* 80065A38: built-in program C91 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C91(struct Entity *e) {
    s32 sp10;
    s16 temp_v1_2;
    s16 var_v0;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a1;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_v0_3;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_2;
    u32 temp_a1_4;
    u32 temp_a1_5;

    rel_tile(e, &sp10);
    if (e->target_anim != 2) {
        temp_a1 = e->mpx;
        temp_a0 = temp_a1 - g_ent->atk_x;
        if (temp_a0 >= 0) {
            if (temp_a0 < (g_ent->atk_w + 1)) {
                goto block_5;
            }
            goto block_14;
        }
        if ((g_ent->atk_x - temp_a1) < (e->sizex + 1)) {
block_5:
            temp_a1_2 = e->mpy;
            temp_a0_2 = temp_a1_2 - g_ent->atk_y;
            if (temp_a0_2 >= 0) {
                if (temp_a0_2 < (g_ent->atk_h + 1)) {
                    goto block_9;
                }
                goto block_14;
            }
            if ((g_ent->atk_y - temp_a1_2) < (e->sizey + 1)) {
block_9:
                temp_a1_3 = e->mpz;
                temp_a0_3 = temp_a1_3 - g_ent->atk_z;
                if (temp_a0_3 >= 0) {
                    if (temp_a0_3 < (g_ent->atk_d + 1)) {
                        goto block_13;
                    }
                    goto block_14;
                }
                if ((g_ent->atk_z - temp_a1_3) < (e->sizez + 1)) {
block_13:
                    play_sound(0x1D6);
                    e->bytes[0] = 2;
                    e->target_anim = 2;
                    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                    e->ai[1] = 0x258;
                    return;
                }
                goto block_14;
            }
            goto block_14;
        }
        goto block_14;
    }
block_14:
    temp_v0 = (u16) e->ai[4];
    var_v0 = temp_v0 - 1;
    if (temp_v0 == 0) {
        if ((sp10 < 9) && (sp14 < 9) && !(g_mode_flags & 4)) {
            play_sound(0x1D6);
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
            var_v0 = ((temp_lo_2 + 0xE06A02E7) / MULHI_11) + 0x19;
        }
    }
    e->ai[4] = var_v0;
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        temp_v0_2 = (u16) e->ai[1];
        if (temp_v0_2 != 0) {
            e->ai[1] = temp_v0_2 - 1;
            return;
        }
        e->bytes[0] = 1;
        e->ai[1] = 0x78;
        temp_lo_3 = g_rng_seed * 0x7D2B89DD;
        temp_a1_4 = temp_lo_3 + 0xE06A02E7;
        e->target_anim = 1;
        g_rng_seed = temp_a1_4;
        temp_lo_4 = temp_a1_4 * 0x7D2B89DD;
        if (((temp_lo_3 + 0xE06A02E7) / MULHI_3) == 0) {
            g_rng_seed = temp_lo_4 + 0xE06A02E7;
            e->target_dir = (temp_lo_4 + 0xE06A02E7) / 134217728;
            return;
        }
        return;
    default:
        temp_v1_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v1_2;
        if (!(temp_v1_2 & 0xFFFF)) {
            e->target_anim = 0;
            e->ai[1] = 0x50;
            return;
        }
        if (!(temp_v1_2 & 0x3F)) {
            temp_lo_5 = g_rng_seed * 0x7D2B89DD;
            temp_a1_5 = temp_lo_5 + 0xE06A02E7;
            g_rng_seed = temp_a1_5;
            temp_lo_6 = temp_a1_5 * 0x7D2B89DD;
            if (((temp_lo_5 + 0xE06A02E7) / MULHI_3) == 0) {
                g_rng_seed = temp_lo_6 + 0xE06A02E7;
                e->target_dir = (e->target_dir + (((temp_lo_6 + 0xE06A02E7) / MULHI_13) - 6)) & 0x1F;
            }
        }
        if (e->force_adjusted != 0) {
            temp_v0_3 = e->target_anim;
            e->bytes[0] = (u8) temp_v0_3;
            step_or_turn(e, temp_v0_3 & 0xFF, 3, 0x200000);
            if (e->target_anim == e->bytes[0]) {
                temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_7 + 0xE06A02E7;
                if (((temp_lo_7 + 0xE06A02E7) / 2147483648) != 0) {
                    e->target_dir = (e->target_dir + 0x10) & 0x1F;
                    return;
                }
            }
            ledge_turn(e, (s32) e->bytes[0], 0x400000);
            return;
        }
        break;
    case 3:
        if (e->on_ground != 0) {
            e->target_anim = (s32) e->bytes[0];
        }
        break;
    }
}
