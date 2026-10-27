/* 80072AC8: built-in program C40 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_8004A7B4(?);                                 /* extern */
? func_80083394(struct Entity *);                   /* extern */

void AI_C40(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_3;
    s16 temp_v0_6;
    s16 temp_v0_8;
    s16 var_v0_4;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 var_a0;
    s32 var_s1;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v1;
    u16 temp_v0_4;
    u16 temp_v0_5;
    u32 temp_v1_4;
    u8 temp_v0_7;
    u8 temp_v1;
    u8 temp_v1_5;
    u8 var_v0_3;

    temp_v0 = e->delay;
    temp_v0_2 = temp_v0 - 1;
    if (temp_v0 != 0) {
        e->delay = temp_v0_2;
        if (temp_v0_2 == 0) {
            *(s32 *)0x801F94D0 = 0;
            func_8004A7B4(0x55);
        }
    }
    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394(e);
            return;
        }
        e->target_anim = 0xA;
        e->flags |= 0x40;
        return;
    }
    temp_v1_2 = e->target_anim;
    if (temp_v1_2 != 1) {
        if (temp_v1_2 != 0xD) {
            e->item_state = 0;
        }
    }
    rel_tile(e, &sp20);
    temp_v1_3 = e->target_anim;
    switch (temp_v1_3) {                            /* switch 1 */
    case 6:                                         /* switch 1 */
        if (sees_player(e, &sp20, 3, 3, 0) != 0) {
            e->target_anim = 0xB;
            e->ai[1] = 0x78;
            var_v1 = -0x101;
block_74:
            e->flags &= var_v1;
            return;
        }
    default:                                        /* switch 1 */
        return;
    case 11:                                        /* switch 1 */
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (!(temp_v0_3 & 0xFFFF)) {
            e->target_anim = 7;
            e->flags |= 0x100;
            return;
        }
        break;
    case 7:                                         /* switch 1 */
        if (e->on_ground != 0) {
            e->target_anim = 0;
            play_sound(0x65);
            return;
        }
        break;
    case 0:                                         /* switch 1 */
        if (e->bytes[2] == 0) {
            temp_v0_4 = (u16) e->ai[1];
            if (temp_v0_4 != 0) {
                e->ai[1] = temp_v0_4 - 1;
                return;
            }
            if (((u16) e->ai[4] == 0) || (temp_v1_4 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7, g_rng_seed = temp_v1_4, (((s32) MULTU_HI(temp_v1_4, ((u16) e->ai[4] + 1)) >> 0) != 0))) {
                e->ai[4] = 0;
                if (e->bytes[1] != 0) {
                    start_moving(e, 1, 0x3C, 0x46);
                    e->bytes[0] = 2;
                    return;
                }
                if ((sp20 < 3) && (sp24 < 3)) {
                    if (sp28 <= 0x100000) {
                        e->target_anim = 1;
                        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                        e->ai[1] = 0x78;
                        e->bytes[0] = 1;
                        return;
                    }
                    goto block_32;
                }
block_32:
                start_moving(e, 1, 0x78, 0x14);
                e->bytes[0] = 0;
                return;
            }
block_49:
            e->target_anim = 2;
            e->target_dir = 0;
            e->ai[1] = 0x3C;
            return;
        }
        break;
    case 1:                                         /* switch 1 */
    case 13:                                        /* switch 1 */
        var_v0 = e->hp_max;
        if (var_v0 < 0) {
            var_v0 += 3;
        }
        if ((var_v0 >> 2) >= e->hp) {
            e->target_anim = 0xD;
        }
        if (e->item_state == 0) {
            play_sound(0x1CF);
            var_v0_2 = 0x10;
            if (e->target_anim == 1) {
                var_v0_2 = 0x1A;
            }
            e->item_state = var_v0_2;
        }
        e->bytes[1] = 0;
        e->item_state -= 1;
        temp_v1_5 = e->bytes[0];
        e->ai[1] = (u16) e->ai[1] - 1;
        switch (temp_v1_5) {                        /* switch 2; irregular */
        case 0:                                     /* switch 2 */
            if ((u16) e->ai[1] == 0) {
                goto block_49;
            }
            var_v0_3 = 2;
            if (sees_player(e, &sp20, 1, 5, 0x100000) == 0) {
                if (e->force_adjusted != 0) {
                    e->target_dir = (e->target_dir + 8) & 0x1F;
                    return;
                }
            } else {
block_55:
                e->bytes[1] = var_v0_3;
                e->target_anim = 0xC;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x3C;
                return;
            }
            break;
        case 1:                                     /* switch 2 */
            var_v0_3 = 3;
            if (((u16) e->ai[1] == 0) || (var_v0_3 = 3, (e->force_adjusted != 0))) {
                goto block_55;
            }
            break;
        case 2:                                     /* switch 2 */
            if (((u16) e->ai[1] == 0) || (e->force_adjusted != 0)) {
                e->target_anim = 0;
                e->ai[1] = 0x28;
                return;
            }
            break;
        }
        break;
    case 2:                                         /* switch 1 */
        temp_v0_5 = (u16) e->ai[1];
        temp_v0_6 = temp_v0_5 - 1;
        if (temp_v0_5 != 0) {
            e->ai[1] = temp_v0_6;
            if (!(temp_v0_6 & 0xFFFF)) {
                play_sound(0x55);
                *(void *)0x801F94D0 = 1;
                *(s32 *)0x801F94DC = 1;
                *(s32 *)0x801F94E0 = 1;
                *(s32 *)0x801F94D4 = 2;
                *(s32 *)0x801F94D8 = 2;
                e->delay = 0x28;
            }
        }
        if (e->anim_done != 0) {
            e->ai[1] = 0x3C;
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            temp_v0_7 = ((temp_lo + 0xE06A02E7) / 1073741824) + 4;
            e->bytes[1] = temp_v0_7;
            if ((temp_v0_7 & 0xFF) == 4) {
block_70:
                spawn_warp_entity(e, 1, 0xF3, e->px, /* extra? */ e->pz, /* extra? */ e->target_dir);
                return;
            }
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            var_s1 = (temp_lo_2 + 0xE06A02E7) / 1073741824;
            if (var_s1 < 0x20) {
                do {
                    var_s1 += 4;
                    spawn_warp_entity(e, 1, 0xF3, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ var_s1);
                } while (var_s1 < 0x20);
                return;
            }
        }
        break;
    case 12:                                        /* switch 1 */
        temp_v0_8 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_8;
        if (!(temp_v0_8 & 0xFFFF)) {
            e->target_anim = 0;
            e->ai[1] = 0xF;
            goto block_70;
        }
        break;
    case 9:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                var_v1 = -4;
                e->target_anim = 0;
                goto block_74;
            }
            e->target_anim = 0;
            e->damaged_tick = 0x5A;
            e->ai[4] = 0;
            if (e->bytes[2] == 0) {
                var_a0 = e->hp_max;
                e->ai[1] = 0x14;
                if (var_a0 < 0) {
                    var_a0 += 3;
                }
                var_v0_4 = 2;
                if ((var_a0 >> 2) >= e->hp) {
                    var_v0_4 = 1;
                }
                e->ai[4] = var_v0_4;
            }
        }
        break;
    }
}
