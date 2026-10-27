/* 800736A4: built-in program C43 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_800277FC;
extern ? D_80027800;

void AI_C43(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_14;
    s16 temp_v0_4;
    s16 temp_v0_5;
    s16 temp_v0_6;
    s16 temp_v0_7;
    s16 temp_v0_9;
    s16 var_v0;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_10;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_lo_9;
    s32 temp_v0;
    s32 temp_v0_11;
    s32 temp_v0_12;
    s32 temp_v0_2;
    s32 temp_v1_2;
    s32 var_a0;
    s32 var_hi;
    s32 var_s1;
    s32 var_v0_2;
    struct Entity *temp_v0_15;
    u16 temp_v0_13;
    u16 temp_v0_3;
    u32 temp_a1;
    u32 temp_v1_3;
    u32 temp_v1_4;
    u32 var_v1;
    u8 temp_a0_3;
    u8 temp_v0_10;
    u8 temp_v0_8;
    u8 temp_v1;
    u8 temp_v1_5;
    u8 temp_v1_6;

    temp_v0 = e->item_state;
    temp_v0_2 = temp_v0 - 1;
    if (temp_v0 != 0) {
        e->item_state = temp_v0_2;
        if (temp_v0_2 == 0) {
            *(s32 *)0x801F94D0 = 0;
        }
    }
    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394(e);
            return;
        }
        e->target_anim = 9;
        e->flags |= 0x40;
        return;
    }
    rel_tile(e, &sp20);
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {                            /* switch 1 */
    case 0:                                         /* switch 1 */
        temp_v0_3 = (u16) e->ai[1];
        temp_v0_4 = temp_v0_3 - 1;
        if ((temp_v0_3 == 0) || (e->ai[1] = temp_v0_4, ((temp_v0_4 & 0xFFFF) == 0))) {
            if ((sp20 < 5) && (sp24 < 5) && (sp28 <= 0x100000)) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                temp_v1_3 = temp_lo + 0xE06A02E7;
                g_rng_seed = temp_v1_3;
                temp_a0 = (temp_lo + 0xE06A02E7) / 1073741824;
                switch (temp_a0) {                  /* switch 2; irregular */
                case 0:                             /* switch 2 */
                    e->target_anim = 5;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->ai[1] = 0x3C;
                    e->bytes[1] = 1;
                    e->bytes[2] = 0xA;
                    return;
                case 1:                             /* switch 2 */
                    e->target_dir = 0x10;
                    e->target_anim = 1;
                    e->bytes[1] = 3;
                    return;
                case 2:                             /* switch 2 */
                    temp_lo_2 = temp_v1_3 * 0x7D2B89DD;
                    var_v1 = temp_lo_2 + 0xE06A02E7;
                    var_hi = (temp_lo_2 + 0xE06A02E7) / 134217728;
                    e->target_anim = 1;
                    goto block_36;
                case 3:                             /* switch 2 */
                    e->target_anim = 3;
                    var_v0 = 0x22;
block_114:
                    e->ai[1] = var_v0;
                    break;
                }
            } else {
                temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                temp_v1_4 = temp_lo_3 + 0xE06A02E7;
                g_rng_seed = temp_v1_4;
                temp_a0_2 = (temp_lo_3 + 0xE06A02E7) / 1073741824;
                switch (temp_a0_2) {                /* switch 3; irregular */
                case 0:                             /* switch 3 */
                    e->target_anim = 1;
                    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                    e->ai[1] = 0x50;
                    e->bytes[1] = 5;
                    return;
                case 1:                             /* switch 3 */
                    /* fallthrough */
                case 3:                             /* switch 3 */
                    temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                    var_v1 = temp_lo_4 + 0xE06A02E7;
                    var_hi = (temp_lo_4 + 0xE06A02E7) / 134217728;
                    e->target_anim = 1;
block_36:
                    g_rng_seed = var_v1;
                    e->ai[1] = 0x3C;
                    e->bytes[1] = 6;
                    e->bytes[2] = 3;
                    e->target_dir = var_hi >> 0;
                    return;
                case 2:                             /* switch 3 */
                    temp_lo_5 = temp_v1_4 * 0x7D2B89DD;
                    e->target_anim = 5;
                    g_rng_seed = temp_lo_5 + 0xE06A02E7;
                    e->ai[1] = 0x1E;
                    e->bytes[1] = 7;
                    e->bytes[2] = 5;
                    e->target_dir = (((temp_lo_5 + 0xE06A02E7) / 1073741824) * 8) + 4;
                    return;
                }
            }
        } else {
        default:                                    /* switch 1 */
            return;
        }
        break;
    case 2:                                         /* switch 1 */
        if (e->anim_done != 0) {
            temp_a0_3 = e->bytes[1];
            if ((temp_a0_3 & 0xFF) == 3) {
                var_s1 = 0;
                do {
                    temp_a3 = *(&D_800277FC + var_s1);
                    var_s1 += 8;
                    spawn_warp_entity(e, 1, 0xFC, temp_a3, /* extra? */ *(&D_80027800 + var_s1), /* extra? */ (e->pz + 0xF00000), /* extra? */ 0);
                } while (var_s1 != 0x20);
                e->target_anim = 0;
                e->ai[1] = 0xB4;
                e->delay += 4;
                return;
            }
            e->bytes[1] = temp_a0_3 + 1;
            e->cur_anim = -1;
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v1_5 = e->bytes[1];
        switch (temp_v1_5) {                        /* switch 4; irregular */
        case 3:                                     /* switch 4 */
            temp_v0_5 = (u16) e->ai[1] + 1;
            e->ai[1] = temp_v0_5;
            if ((u32) (temp_v0_5 & 0xFFFF) >= 0x1EU) {
                var_v0 = 0x22;
                if (e->force_adjusted != 0) {
                    e->target_anim = (s32) temp_v1_5;
                    goto block_114;
                }
            }
            break;
        case 5:                                     /* switch 4 */
            temp_v0_6 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_6;
            if (!(temp_v0_6 & 0xFFFF) || (e->force_adjusted != 0)) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                var_v0 = 0x28;
                if (sp20 < 9) {
                    if (sp24 < 9) {
                        e->target_anim = 3;
                        e->ai[1] = 0x22;
                        e->bytes[1] = 4;
                        return;
                    }
block_112:
                    var_v0 = 0x28;
                    goto block_113;
                }
block_113:
                e->target_anim = 0;
                goto block_114;
            }
            break;
        case 6:                                     /* switch 4 */
            temp_v0_7 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_7;
            if (!(temp_v0_7 & 0xFFFF) || (e->force_adjusted != 0)) {
                temp_v0_8 = e->bytes[2] - 1;
                e->bytes[2] = temp_v0_8;
                if (temp_v0_8 & 0xFF) {
                    temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_6 + 0xE06A02E7;
                    e->target_dir = (temp_lo_6 + 0xE06A02E7) / 134217728;
                } else {
                    e->target_anim = 0;
                }
                temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_7 + 0xE06A02E7;
                var_v0 = ((temp_lo_7 + 0xE06A02E7) / 268435456) + 0x28;
                goto block_114;
            }
            break;
        default:                                    /* switch 4 */
            temp_v0_9 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_9;
            var_v0 = 0x28;
            if (!(temp_v0_9 & 0xFFFF)) {
                goto block_113;
            }
            break;
        }
        break;
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[1] == 1) {
                e->target_anim = 0xA;
                return;
            }
            e->target_anim = 6;
            return;
        }
        break;
    case 6:                                         /* switch 1 */
    case 10:                                        /* switch 1 */
        temp_v1_6 = e->bytes[1];
        switch (temp_v1_6) {                        /* switch 5; irregular */
        case 1:                                     /* switch 5 */
            e->ai[1] = (u16) e->ai[1] - 1;
            /* fallthrough */
        case 7:                                     /* switch 5 */
            if (((u16) e->ai[1] == 0) || (e->force_adjusted != 0)) {
                temp_v0_10 = e->bytes[2] - 1;
                e->bytes[2] = temp_v0_10;
                if (temp_v0_10 & 0xFF) {
                    e->sfy = 0;
                    e->sfx = 0;
                    e->fy = 0;
                    e->fx = 0;
                    e->tfy = 0;
                    e->tfx = 0;
                    if (e->bytes[1] == 7) {
                        temp_v0_11 = e->mpx;
                        if (((temp_v0_11 + 0xFFFF0000) <= 0x01080000) || ((temp_v0_11 + e->sizex + 0x10001) > 0x0287FFFF)) {
                            var_v0_2 = 0x20;
                            goto block_84;
                        }
                        temp_v0_12 = e->mpy;
                        if (((temp_v0_12 + 0xFFFF0000) <= 0x01000000) || ((temp_v0_12 + e->sizey + 0x10001) > 0x01FFFFFF)) {
                            var_v0_2 = 0x10;
block_84:
                            e->target_dir = (var_v0_2 - e->target_dir) & 0x1F;
                            return;
                        }
                    } else {
                        temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                        temp_a1 = temp_lo_8 + 0xE06A02E7;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        g_rng_seed = temp_a1;
                        temp_lo_9 = temp_a1 * 0x7D2B89DD;
                        if (((temp_lo_8 + 0xE06A02E7) / MULHI_3) == 0) {
                            g_rng_seed = temp_lo_9 + 0xE06A02E7;
                            e->target_dir = ((e->target_dir + ((temp_lo_9 + 0xE06A02E7) / MULHI_9)) - 4) & 0x1F;
                        }
                        var_v0 = 0x1E;
                        goto block_114;
                    }
                } else {
                    var_v0 = 0x3C;
                    goto block_113;
                }
            }
            break;
        }
        break;
    case 3:                                         /* switch 1 */
        temp_v0_13 = (u16) e->ai[1];
        temp_v0_14 = temp_v0_13 - 1;
        if (temp_v0_13 != 0) {
            e->ai[1] = temp_v0_14;
            if (!(temp_v0_14 & 0xFFFF)) {
                temp_v0_15 = spawn_warp_entity(e, 1, 0xFB, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x300000), /* extra? */ dir_from_delta(g_ent->px - e->px, g_ent->py - e->py));
                if (temp_v0_15 != NULL) {
                    if ((sp20 < 6) && (sp24 < 6)) {
                        temp_v0_15->target_anim = 2;
                        return;
                    }
                    if (sp20 < 9) {
                        if (sp24 < 9) {
                            temp_v0_15->target_anim = 3;
                            return;
                        }
                        goto block_99;
                    }
block_99:
                    temp_v0_15->target_anim = 4;
                    return;
                }
            }
        }
        break;
    case 4:                                         /* switch 1 */
        if (e->on_ground != 0) {
            e->target_anim = 0;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            var_v0 = 0x14;
            goto block_114;
        }
        break;
    case 8:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                *(void *)0x801F94D0 = 0;
                return;
            }
            var_a0 = e->hp_max;
            e->damaged_tick = 0x5A;
            if (var_a0 < 0) {
                var_a0 += 3;
            }
            if (((var_a0 >> 2) >= e->hp) && (e->delay < 4)) {
                e->target_anim = 2;
                e->bytes[1] = 0;
                return;
            }
            temp_lo_10 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_10 + 0xE06A02E7;
            var_v0 = 0x28;
            if (((temp_lo_10 + 0xE06A02E7) / 1073741824) == 0) {
                e->target_anim = 3;
                e->ai[1] = 0x22;
                goto block_112;
            }
            goto block_113;
        }
        break;
    }
}
