/* 8006F278: built-in program C30 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C30(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 temp_v0_3;
    s32 temp_a0_2;
    s32 temp_a1_2;
    s32 temp_a2;
    s32 temp_lo;
    s32 temp_lo_10;
    s32 temp_lo_11;
    s32 temp_lo_12;
    s32 temp_lo_13;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_lo_9;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v1;
    s32 var_hi;
    s32 var_hi_2;
    s32 var_v0;
    struct Entity *temp_v0_4;
    u32 temp_a1;
    u32 temp_v1_2;
    u8 temp_a0;

    rel_tile_z(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 9:                                         /* switch 1 */
        if ((sp20 < 5) && (sp24 < 5) && (sp28 <= 0x200000)) {
            play_sound(0x171);
            e->target_anim = 2;
            e->bytes[0] = 1;
            return;
        }
    default:                                        /* switch 1 */
        return;
    case 2:                                         /* switch 1 */
        if ((e->anim_done != 0) && (e->bytes[0] == 1)) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 7;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / 268435456) + 0x12C;
            return;
        }
        break;
    case 0:                                         /* switch 1 */
        temp_lo_2 = g_rng_seed * 0x7D2B89DD;
        temp_v1_2 = temp_lo_2 + 0xE06A02E7;
        temp_lo_3 = temp_v1_2 * 0x7D2B89DD;
        sp38 = temp_v1_2 * 0x20;
        sp3C = (temp_lo_2 + 0xE06A02E7) / 134217728;
        e->target_anim = 1;
        g_rng_seed = temp_v1_2;
        g_rng_seed = temp_lo_3 + 0xE06A02E7;
        e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
        e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 134217728) + 0x50;
        return;
    case 1:                                         /* switch 1 */
    case 7:                                         /* switch 1 */
    case 8:                                         /* switch 1 */
        temp_v0 = e->delay;
        temp_v0_2 = temp_v0 - 1;
        if (((temp_v0 == 0) || (e->delay = temp_v0_2, (temp_v0_2 == 0))) && (e->bytes[1] == 0) && (e->bytes[2] == 0) && (sp34 >= 0) && (sees_player(e, &sp20, 2, 5, 0x400000) != 0)) {
            e->target_anim = 1;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x32;
            e->bytes[2] = 4;
            return;
        }
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (!(temp_v0_3 & 0xFFFF)) {
            if (e->bytes[2] != 0) {
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                if (((temp_lo_4 + 0xE06A02E7) / MULHI_3) == 0) {
                    play_sound(0x171);
                }
                temp_v0_4 = spawn_warp_entity(e, 1, 0xDA, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x100000), /* extra? */ e->target_dir);
                if (temp_v0_4 != NULL) {
                    temp_v0_4->fz = -0x10000;
                    temp_v0_4->flags &= ~0x100;
                }
                temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_5 + 0xE06A02E7;
                temp_a0 = e->bytes[2] - 1;
                e->bytes[2] = temp_a0;
                e->ai[1] = ((temp_lo_5 + 0xE06A02E7) / 268435456) + 0x32;
                if (!(temp_a0 & 0xFF)) {
                    temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                    var_hi = (temp_lo_6 + 0xE06A02E7) / 134217728;
                    e->delay = 0x32;
                    g_rng_seed = temp_lo_6 + 0xE06A02E7;
                    goto block_47;
                }
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                return;
            }
            if (e->on_ground != 0) {
                temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                var_hi_2 = (temp_lo_7 + 0xE06A02E7) / 134217728;
                e->target_anim = 7;
                g_rng_seed = temp_lo_7 + 0xE06A02E7;
                goto block_45;
            }
            temp_lo_8 = g_rng_seed * 0x7D2B89DD;
            temp_a1 = temp_lo_8 + 0xE06A02E7;
            g_rng_seed = temp_a1;
            temp_lo_9 = temp_a1 * 0x7D2B89DD;
            if (((temp_lo_8 + 0xE06A02E7) / MULHI_3) == 0) {
                e->target_anim = 8;
                e->ai[1] = 0x1E;
                return;
            }
            var_hi = (temp_lo_9 + 0xE06A02E7) / 134217728;
            e->target_anim = 1;
            g_rng_seed = temp_lo_9 + 0xE06A02E7;
            e->ai[1] = 0x64;
            e->bytes[1] = 0;
            goto block_47;
        }
        temp_a2 = e->target_anim;
        switch (temp_a2) {                          /* switch 2; irregular */
        case 7:                                     /* switch 2 */
            temp_a1_2 = e->pz;
            if ((temp_a1_2 - ((u16) e->ai[0] << 0x10)) > 0x4FFFFF) {
                var_v0 = 8;
                if ((temp_a1_2 - e->terrain) <= 0x200000) {
                    var_v0 = 1;
                }
                e->target_anim = var_v0;
                temp_lo_10 = g_rng_seed * 0x7D2B89DD;
                var_hi_2 = (temp_lo_10 + 0xE06A02E7) / 134217728;
                g_rng_seed = temp_lo_10 + 0xE06A02E7;
                e->bytes[0] = 0;
                e->bytes[1] = 0;
block_45:
                e->ai[1] = (var_hi_2 >> 0) + 0x28;
                return;
            }
            break;
        case 8:                                     /* switch 2 */
            temp_a0_2 = e->pz - ((u16) e->ai[0] << 0x10);
            if (temp_a0_2 > 0xFFA00000) {
                if (e->on_ground != 0) {
                    if (temp_a0_2 <= 0x200000) {
                        goto block_44;
                    }
                    temp_lo_11 = g_rng_seed * 0x7D2B89DD;
                    var_hi = (temp_lo_11 + 0xE06A02E7) / 134217728;
                    e->target_anim = 1;
                    g_rng_seed = temp_lo_11 + 0xE06A02E7;
                    e->ai[1] = 0x3C;
block_47:
                    e->target_dir = var_hi >> 0;
                    return;
                }
            } else {
block_44:
                temp_lo_12 = g_rng_seed * 0x7D2B89DD;
                var_hi_2 = (temp_lo_12 + 0xE06A02E7) / MULHI_17;
                e->target_anim = 7;
                g_rng_seed = temp_lo_12 + 0xE06A02E7;
                e->bytes[0] = 1;
                goto block_45;
            }
            break;
        case 1:                                     /* switch 2 */
            if (e->force_adjusted != 0) {
                temp_lo_13 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_13 + 0xE06A02E7;
                e->ai[1] = 0x28;
                e->target_dir = (temp_lo_13 + 0xE06A02E7) / 134217728;
                if (e->bytes[0] == temp_a2) {
                    e->target_anim = 7;
                    return;
                }
                e->target_anim = 8;
                return;
            }
            break;
        }
        break;
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 6;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 7;
            e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
            e->ai[1] = 0x78;
            e->bytes[1] = 1;
        }
        break;
    }
}
