/* 80074CC0: built-in program C46 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
s32 func_80082C30(struct Entity *, s32 *, ?, ?, s32, s32); /* extern */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_800279E0;
extern ? D_80028AF8;

void AI_C46(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp50;
    s32 sp54;
    s16 temp_v0;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 temp_v0_9;
    s16 temp_v1_4;
    s16 var_v0_4;
    s32 *var_s5;
    s32 *var_s7;
    s32 temp_lo;
    s32 temp_lo_10;
    s32 temp_lo_11;
    s32 temp_lo_12;
    s32 temp_lo_13;
    s32 temp_lo_14;
    s32 temp_lo_15;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_lo_9;
    s32 temp_v0_6;
    s32 temp_v1;
    s32 var_fp;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v1;
    struct Entity *temp_s6;
    struct Entity *temp_v0_10;
    struct Entity *temp_v0_11;
    struct Entity *temp_v0_7;
    struct Entity *temp_v0_8;
    struct Entity *var_s2;
    struct Entity *var_s3;
    u16 temp_v1_2;
    u32 temp_a0_2;
    u32 temp_a1;
    u32 temp_a1_2;
    u32 temp_a1_3;
    u32 temp_a2;
    u8 temp_a0;
    u8 temp_v0_12;
    u8 temp_v0_3;
    u8 temp_v0_5;
    u8 temp_v1_3;

    temp_s6 = e->unk284;
    rel_tile(e, &sp20);
    rel_tile(temp_s6, &sp38);
    var_s2 = e;
    if (e->px < temp_s6->px) {
        e->bytes[2] = 0;
        var_s3 = temp_s6;
        var_s5 = &sp20;
        var_s7 = &sp38;
    } else {
        e->bytes[2] = 1;
        var_s2 = temp_s6;
        var_s3 = e;
        var_s5 = &sp38;
        var_s7 = &sp20;
    }
    temp_a0 = e->bytes[3];
    if (temp_a0 != 0) {
        temp_v1 = e->target_anim;
        if ((temp_v1 == 3) || (var_v0 = (u32) temp_v1 < 0x16U, (temp_v1 == 0))) {
            if (temp_a0 < 4U) {
                func_80083394(e);
                func_80083394(temp_s6);
                return;
            }
            e->target_anim = 0xB;
            e->flags |= 0x40;
            temp_s6->anim_done = 0;
            temp_s6->flags |= 0x40;
            return;
        }
        goto block_10;
    }
    var_v0 = (u32) e->target_anim < 0x16U;
block_10:
    var_fp = 0;
    if (var_v0 != 0) {
        switch (e->target_anim) {                   /* switch 1 */
        case 0:                                     /* switch 1 */
        case 3:                                     /* switch 1 */
            temp_v1_2 = (u16) e->ai[1];
            e->target_anim = 3;
            if ((temp_v1_2 == 0) || (temp_v0 = temp_v1_2 - 1, e->ai[1] = temp_v0, ((temp_v0 & 0xFFFF) == 0))) {
                e->target_anim = 2;
                if ((var_s3->px - var_s2->px) <= 0x480000) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    temp_a1 = temp_lo + 0xE06A02E7;
                    g_rng_seed = temp_a1;
                    if (((temp_lo + 0xE06A02E7) / 2147483648) != 0) {
                        temp_lo_2 = temp_a1 * 0x7D2B89DD;
                        if (var_s2 == e) {
                            g_rng_seed = temp_lo_2 + 0xE06A02E7;
                            var_v0_2 = ((temp_lo_2 + 0xE06A02E7) / MULHI_9) + 4;
                        } else {
                            g_rng_seed = temp_lo_2 + 0xE06A02E7;
                            var_v0_2 = ((temp_lo_2 + 0xE06A02E7) / MULHI_9) + 0x14;
                        }
                        e->target_dir = var_v0_2;
                        e->bytes[0] = 1;
                        e->ai[1] = 0x50;
                        e->bytes[1] = 7;
                    } else {
                        goto block_21;
                    }
                } else {
block_21:
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    temp_a0_2 = (temp_lo_3 + 0xE06A02E7) / MULHI_6;
                    switch (temp_a0_2) {            /* switch 2 */
                    case 0:                         /* switch 2 */
                        e->bytes[0] = 1;
                        temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                        temp_a2 = temp_lo_4 + 0xE06A02E7;
                        temp_lo_5 = temp_a2 * 0x7D2B89DD;
                        sp50 = temp_a2 * 2;
                        sp54 = (temp_lo_4 + 0xE06A02E7) / 2147483648;
                        g_rng_seed = temp_a2;
                        g_rng_seed = temp_lo_5 + 0xE06A02E7;
                        e->bytes[1] = 1;
                        e->target_dir = (s32) *(((temp_lo_4 + 0xE06A02E7) / 2147483648) + &D_80028AF8);
                        e->ai[1] = ((temp_lo_5 + 0xE06A02E7) / MULHI_21) + 0x64;
                        break;
                    case 1:                         /* switch 2 */
                        e->bytes[0] = 2;
                        temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_6 + 0xE06A02E7;
                        e->bytes[1] = 2;
                        e->target_dir = (temp_lo_6 + 0xE06A02E7) / 134217728;
                        break;
                    case 3:                         /* switch 2 */
                    case 5:                         /* switch 2 */
                        e->bytes[0] = 5;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->ai[1] = 0x3C;
                        e->bytes[1] = 4;
                        break;
                    case 2:                         /* switch 2 */
                    case 4:                         /* switch 2 */
                        e->bytes[0] = 5;
                        temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                        temp_a1_2 = temp_lo_7 + 0xE06A02E7;
                        g_rng_seed = temp_a1_2;
                        temp_lo_8 = temp_a1_2 * 0x7D2B89DD;
                        if (((temp_lo_7 + 0xE06A02E7) / 2147483648) != 0) {
                            g_rng_seed = temp_lo_8 + 0xE06A02E7;
                            e->target_dir = (temp_lo_8 + 0xE06A02E7) / 134217728;
                        } else if (sp30 >= 0) {
                            e->target_dir = 0x10;
                        } else {
                            e->target_dir = 0;
                        }
                        e->ai[1] = 0x3C;
                        e->bytes[1] = 5;
                        break;
                    }
                }
            }
            break;
        case 1:                                     /* switch 1 */
        case 2:                                     /* switch 1 */
            e->target_anim = 2;
            if (func_80082C30(var_s2, var_s5, 2, 4, 6, 2) != 0) {
                e->target_anim = 0x15;
                e->bytes[0] = 1;
                e->ai[1] = 0x3C;
                var_v1 = dir_from_delta(g_ent->px - var_s2->px, g_ent->py - var_s2->py);
                if (e != var_s2) {
                    var_v0_3 = 0x20 - var_v1;
                    goto block_82;
                }
                goto block_37;
            }
            if (func_80082C30(var_s3, var_s7, 3, 4, 6, 2) != 0) {
                e->target_anim = 0x15;
                e->bytes[0] = 1;
                e->ai[1] = 0x3C;
                var_v1 = dir_from_delta(g_ent->px - var_s3->px, g_ent->py - var_s3->py);
                if (e == var_s3) {
block_37:
                    e->target_dir = var_v1;
                } else {
                    var_v0_3 = 0x20 - var_v1;
                    goto block_82;
                }
            } else {
                temp_v1_3 = e->bytes[1];
                switch (temp_v1_3) {                /* switch 3 */
                case 0:                             /* switch 3 */
                case 7:                             /* switch 3 */
                    temp_v0_2 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_2;
                    if (!(temp_v0_2 & 0xFFFF) || (e->force_adjusted != 0) || (temp_s6->force_adjusted != 0)) {
                        var_fp = 1;
                        e->target_anim = 3;
block_126:
                        e->ai[1] = 0x28;
                    }
                    break;
                case 2:                             /* switch 3 */
                    if ((e->force_adjusted != 0) || (temp_s6->force_adjusted != 0)) {
                        temp_v0_3 = e->bytes[0] - 1;
                        e->bytes[0] = temp_v0_3;
                        if (!(temp_v0_3 & 0xFF)) {
                            e->target_anim = 3;
                            var_v0_4 = 0x1E;
block_70:
                            e->ai[1] = var_v0_4;
                        } else {
                            temp_lo_9 = g_rng_seed * 0x7D2B89DD;
                            g_rng_seed = temp_lo_9 + 0xE06A02E7;
                            e->target_dir = (e->target_dir + ((temp_lo_9 + 0xE06A02E7) / MULHI_7) + 9) & 0x1F;
                        }
                        var_fp = 1;
                    }
                    break;
                case 1:                             /* switch 3 */
                case 4:                             /* switch 3 */
                case 5:                             /* switch 3 */
                    if ((var_s2->tile_x == (var_s3->tile_x - 0xA)) && (func_80082C30(var_s2, var_s5, 3, 6, 8, 1) != 0) && (func_80082C30(var_s3, var_s7, 2, 6, 8, 1) != 0)) {
                        e->target_anim = 0xF;
                        if (sp30 >= 0) {
                            e->target_dir = 0x10;
                        } else {
                            e->target_dir = 0;
                        }
                    } else {
                        temp_v0_4 = (u16) e->ai[1] - 1;
                        e->ai[1] = temp_v0_4;
                        if (!(temp_v0_4 & 0xFFFF)) {
                            temp_v0_5 = e->bytes[0] - 1;
                            e->bytes[0] = temp_v0_5;
                            if (!(temp_v0_5 & 0xFF)) {
                                e->target_anim = 3;
                                e->ai[1] = 0x1E;
                            } else {
                                if (e->bytes[1] == 4) {
                                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                                } else {
                                    temp_lo_10 = g_rng_seed * 0x7D2B89DD;
                                    temp_a1_3 = temp_lo_10 + 0xE06A02E7;
                                    g_rng_seed = temp_a1_3;
                                    if (((temp_lo_10 + 0xE06A02E7) / MULHI_3) != 0) {
                                        temp_lo_11 = temp_a1_3 * 0x7D2B89DD;
                                        if ((var_s3->tile_x - var_s2->tile_x) >= 0xB) {
                                            g_rng_seed = temp_lo_11 + 0xE06A02E7;
                                            temp_v0_6 = (temp_lo_11 + 0xE06A02E7) / MULHI_15;
                                            if (var_s2 == e) {
                                                var_v0_5 = temp_v0_6 + 0x11;
                                            } else {
                                                var_v0_5 = temp_v0_6 + 1;
                                            }
                                        } else {
                                            goto block_67;
                                        }
                                    } else {
block_67:
                                        temp_lo_12 = g_rng_seed * 0x7D2B89DD;
                                        g_rng_seed = temp_lo_12 + 0xE06A02E7;
                                        var_v0_5 = (temp_lo_12 + 0xE06A02E7) / 134217728;
                                    }
                                    e->target_dir = var_v0_5;
                                }
                                var_v0_4 = 0x3C;
                                goto block_70;
                            }
                        } else if ((sees_player_q(var_s2, var_s5, 3, 1, 5, 0x100000) != 0) || (sees_player_q(var_s3, var_s7, 2, 1, 5, 0x100000) != 0)) {
                            e->target_anim = 5;
                            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        } else if (((var_s3->tile_x - var_s2->tile_x) >= 4) && (func_80082C30(var_s2, var_s5, 3, 4, 5, 2) != 0) && (func_80082C30(var_s3, var_s7, 2, 4, 5, 2) != 0)) {
                            e->target_anim = 0x15;
                            temp_lo_13 = g_rng_seed * 0x7D2B89DD;
                            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                            g_rng_seed = temp_lo_13 + 0xE06A02E7;
                            e->ai[1] = 0x28;
                            e->bytes[0] = ((temp_lo_13 + 0xE06A02E7) / MULHI_3) + 1;
                        } else if ((e->force_adjusted != 0) || (temp_s6->force_adjusted != 0)) {
                            var_fp = 1;
                            var_v0_3 = e->target_dir + 0x10;
block_82:
                            e->target_dir = var_v0_3 & 0x1F;
                        }
                    }
                    break;
                }
            }
            break;
        case 4:                                     /* switch 1 */
        case 5:                                     /* switch 1 */
            e->target_anim = 5;
            if (e->anim_done != 0) {
                start_moving(e, 2, 0x1E, 0x3C);
                e->bytes[1] = 0;
            }
            break;
        case 12:                                    /* switch 1 */
        case 15:                                    /* switch 1 */
            e->target_anim = 0xF;
            if (e->anim_done != 0) {
                e->target_anim = 0x10;
                e->ai[1] = 0xB4;
                temp_v0_7 = spawn_warp_entity(var_s2, 1, 0xD6, var_s2->px + 0x300000, /* extra? */ var_s2->py, /* extra? */ (var_s2->pz + 0xC0000), /* extra? */ 0x18);
                if (temp_v0_7 != NULL) {
                    temp_v0_7->target_anim = 1;
                }
                temp_v0_8 = spawn_warp_entity(var_s3, 1, 0xD6, var_s3->px - 0x300000, /* extra? */ var_s3->py, /* extra? */ (var_s3->pz + 0xC0000), /* extra? */ 0);
                if (temp_v0_8 != NULL) {
                    temp_v0_8->target_anim = 1;
                }
            }
            break;
        case 13:                                    /* switch 1 */
        case 16:                                    /* switch 1 */
            temp_v1_4 = (u16) e->ai[1] - 1;
            e->target_anim = 0x10;
            e->ai[1] = temp_v1_4;
            if (!(((temp_v1_4 & 0xFFFF) % 60) & 0xFFFF)) {
                if (sp30 >= 0) {
                    e->target_dir = 0x10;
                } else {
                    e->target_dir = 0;
                }
            }
            if ((u16) e->ai[1] == 0) {
                e->target_anim = 3;
                goto block_126;
            }
            break;
        case 20:                                    /* switch 1 */
        case 21:                                    /* switch 1 */
            e->target_anim = 0x15;
            if (e->anim_done != 0) {
                e->target_anim = 0x13;
            }
            break;
        case 18:                                    /* switch 1 */
        case 19:                                    /* switch 1 */
            e->target_anim = 0x13;
            temp_v0_9 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_9;
            if (!(temp_v0_9 & 7)) {
                temp_v0_10 = spawn_warp_entity(var_s2, 1, 0xF4, var_s2->px, /* extra? */ var_s2->py, /* extra? */ var_s2->pz, /* extra? */ 0x18);
                if (temp_v0_10 != NULL) {
                    temp_v0_10->bi_e = 0x19;
                    temp_v0_10->bi_a = 0;
                    temp_v0_10->bi_c = 0;
                    temp_v0_10->target_anim = 0x11;
                    temp_v0_10->flags |= 0x40;
                }
                temp_v0_11 = spawn_warp_entity(var_s3, 1, 0xF4, var_s3->px, /* extra? */ var_s3->py, /* extra? */ var_s3->pz, /* extra? */ 8);
                if (temp_v0_11 != NULL) {
                    temp_v0_11->bi_e = 0x19;
                    temp_v0_11->bi_a = 0;
                    temp_v0_11->bi_c = 0;
                    temp_v0_11->target_anim = 0xE;
                    temp_v0_11->flags |= 0x40;
                }
            }
            if (((u16) e->ai[1] == 0) || (e->force_adjusted != 0)) {
                temp_v0_12 = e->bytes[0] - 1;
                e->bytes[0] = temp_v0_12;
                if ((temp_v0_12 & 0xFF) && (sees_player_q(var_s2, var_s5, 3, 4, 5, 0x100000) != 0)) {
                    if (sees_player_q(var_s3, var_s7, 2, 4, 5, 0x100000) != 0) {
                        e->target_dir = (dir_from_delta(g_ent->px - e->px, g_ent->py - e->py) + 2) & 0x1C;
                        e->ai[1] = 0x3C;
                    } else {
                        goto block_110;
                    }
                } else {
block_110:
                    e->target_anim = 2;
                    if (var_s2 == e) {
                        temp_lo_14 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_14 + 0xE06A02E7;
                        var_v0_6 = ((temp_lo_14 + 0xE06A02E7) / MULHI_9) + 4;
                    } else {
                        temp_lo_15 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_15 + 0xE06A02E7;
                        var_v0_6 = ((temp_lo_15 + 0xE06A02E7) / MULHI_9) + 0x14;
                    }
                    e->target_dir = var_v0_6;
                    e->ai[1] = 0x3C;
                    e->bytes[1] = 0;
                }
            }
            break;
        case 6:                                     /* switch 1 */
        case 9:                                     /* switch 1 */
            e->target_anim = 9;
            break;
        case 8:                                     /* switch 1 */
        case 11:                                    /* switch 1 */
            e->target_anim = 0xB;
            break;
        case 7:                                     /* switch 1 */
        case 10:                                    /* switch 1 */
            e->target_anim = 0xA;
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    e->target_anim = 3;
                    e->flags &= ~3;
                    temp_s6->flags &= ~3;
                    e->ai[1] = 0x12C;
                    temp_s6->ai[1] = 0x12C;
                    e->ai[5] = 0x1E;
                    temp_s6->ai[5] = 0x1E;
                } else {
                    e->damaged_tick = 0x5A;
                    temp_s6->damaged_tick = 0x5A;
                    if ((var_s3->tile_x - var_s2->tile_x) >= 0xE) {
                        if ((*var_s5 < 3) || (*var_s7 < 3)) {
                            e->target_anim = 0x15;
                            if (sp30 >= 0) {
                                e->target_dir = 0x10;
                            } else {
                                e->target_dir = 0;
                            }
                            e->bytes[0] = 1;
                            goto block_126;
                        }
                        goto block_128;
                    }
block_128:
                    e->target_anim = 3;
                    e->ai[1] = 0xA;
                    e->bytes[1] = 0;
                    e->bytes[0] = 0;
                }
            }
            break;
        }
    }
    if (var_fp != 0) {
        e->sfy = 0;
        e->sfx = 0;
        e->fy = 0;
        e->fx = 0;
        e->tfy = 0;
        e->tfx = 0;
    }
    if (e->bytes[2] == 0) {
        temp_s6->target_anim = (s32) *(&D_800279E0 + (e->target_anim * 2));
    } else {
        temp_s6->target_anim = e->target_anim;
        e->target_anim = (s32) *(&D_800279E0 + (e->target_anim * 2));
    }
    temp_s6->target_dir = (0x20 - e->target_dir) & 0x1F;
    temp_s6->py = e->py;
    temp_s6->tfy = e->tfy;
    temp_s6->fy = e->fy;
    temp_s6->sfy = e->sfy;
    temp_s6->tfx = -e->tfx;
    temp_s6->fx = -e->fx;
    temp_s6->sfx = -e->sfx;
}
