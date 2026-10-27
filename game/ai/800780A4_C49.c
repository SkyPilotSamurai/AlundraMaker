/* 800780A4: built-in program C49 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_8004A7B4(?);                                 /* extern */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_80023654;
extern ? D_80023694;
extern s32 D_80027C3C;
extern ? D_80027C40;
extern s32 D_80027C44;
extern ? D_800282D8;
extern ? D_800286D8;
extern ? D_80028AD8;

void AI_C49(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_15;
    s16 temp_v0_20;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a0_4;
    s32 temp_a0_5;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_a3;
    s32 temp_a3_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_t1;
    s32 temp_t1_2;
    s32 temp_v0;
    s32 temp_v0_10;
    s32 temp_v0_11;
    s32 temp_v0_12;
    s32 temp_v0_13;
    s32 temp_v0_14;
    s32 temp_v0_17;
    s32 temp_v0_18;
    s32 temp_v0_19;
    s32 temp_v0_23;
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v0_8;
    s32 temp_v0_9;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_4;
    s32 temp_v1_7;
    s32 temp_v1_9;
    s32 var_a0;
    s32 var_a0_2;
    s32 var_a0_3;
    s32 var_a1;
    s32 var_s1_2;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v0_8;
    struct Entity *temp_a0;
    struct Entity *temp_a0_6;
    struct Entity *temp_a1;
    struct Entity *temp_v0_21;
    struct Entity *temp_v0_24;
    struct Entity *temp_v0_4;
    u16 temp_v0_5;
    u32 var_s1;
    u8 temp_a2;
    u8 temp_v0_16;
    u8 temp_v0_22;
    u8 temp_v0_6;
    u8 temp_v0_7;
    u8 temp_v1_3;
    u8 temp_v1_5;
    u8 temp_v1_6;
    u8 temp_v1_8;
    u8 var_v0_3;
    u8 var_v0_7;

    if (e->delay == 0) {
        e->delay = 1;
        *(s32 *)0x801247B4 = 0;
        *(s32 *)0x801247B0 = 0;
        *(s32 *)0x801247AC = 0;
        *(s32 *)0x801247A8 = 0;
        *(s32 *)0x801247C4 = 0;
        *(s32 *)0x801247C0 = 0;
        *(s32 *)0x801247BC = 0;
        *(s32 *)0x801247B8 = 0;
        *(s32 *)0x801247D0 = 0;
        *(s32 *)0x801247CC = 0;
        *(s32 *)0x801247C8 = 0;
        *(struct Entity **)0x801247D4 = NULL;
    }
    temp_v0 = *(void *)0x801247D0;
    temp_v0_2 = temp_v0 - 1;
    if (temp_v0 != 0) {
        *(void *)0x801247D0 = temp_v0_2;
        if (temp_v0_2 == 0) {
            *(s32 *)0x801F94D0 = 0;
        }
    }
    if (e->bytes[0] == 6) {
        temp_v0_3 = e->item_state + 1;
        e->item_state = temp_v0_3;
        if (!(temp_v0_3 & 0xF)) {
            temp_a1 = *(void *)0x801247D4;
            if (temp_a1 != NULL) {
                var_a1 = temp_a1->py;
                var_a0 = g_ent->px - temp_a1->px;
            } else {
                var_a1 = e->py;
                var_a0 = g_ent->px - e->px;
            }
            *(void *)0x801247C4 = dir_from_delta(var_a0, g_ent->py - var_a1);
            if (!(e->item_state & 0xF)) {
                if (e->target_anim == 5) {
                    temp_v0_4 = spawn_warp_entity(e, 1, 0xE0, e->px + 0xFFE20000, /* extra? */ (e->py + 0x200000), /* extra? */ e->terrain, /* extra? */ 0);
                    if (temp_v0_4 != NULL) {
                        temp_v0_4->target_anim = 4;
                        temp_v0_4->flags |= 0x40;
                    }
                }
            }
        }
        temp_v1 = e->mpx;
        temp_a3 = *(&D_80023654 + (*(void *)0x801247C4 * 2)) * 0xA0;
        if ((temp_a3 >= 0) || ((temp_v1 + 0xFFFF0000) > 0x900000)) {
            if ((temp_a3 <= 0) || ((temp_v1 + e->sizex + 0x10001) <= 0x020FFFFF)) {
                e->pafx = temp_a3;
            }
        }
        temp_v1_2 = e->mpy;
        temp_t1 = *(&D_80023694 + (*(void *)0x801247C4 * 2)) * 0xA0;
        if (((temp_t1 >= 0) || ((temp_v1_2 + 0xFFFF0000) > 0x02700000)) && ((temp_t1 <= 0) || ((temp_v1_2 + e->sizey + 0x10001) <= 0x038FFFFF))) {
            e->pafy = temp_t1;
        }
        temp_a0 = *(void *)0x801247D4;
        if (temp_a0 != NULL) {
            temp_a0->px = e->px + 0xFFE20000;
            temp_a0->py = e->py + 0x1A0000;
        }
    }
    temp_v1_3 = e->bytes[3];
    if ((temp_v1_3 != 0) && (e->target_anim == 0)) {
        if (temp_v1_3 < 4U) {
            func_80083394(e);
            return;
        }
        e->target_anim = 8;
        e->flags |= 0x40;
        return;
    }
    rel_tile_z(e, &sp20);
    temp_v1_4 = e->target_anim;
    switch (temp_v1_4) {                            /* switch 1 */
    case 0:                                         /* switch 1 */
        temp_v0_5 = (u16) e->ai[1];
        if (temp_v0_5 != 0) {
            e->ai[1] = temp_v0_5 - 1;
            return;
        }
        if (e->bytes[0] == 8) {
            if ((e->pz - e->terrain) > 0x9FFFFF) {
                e->target_anim = 3;
                e->ai[1] = 0;
                e->item_state = 0x1C;
block_159:
                e->flags |= 0x100;
                return;
            }
block_185:
            e->target_anim = 2;
block_186:
            e->bytes[0] = 0;
        } else {
            temp_v0_6 = e->bytes[2];
            temp_v0_7 = temp_v0_6 - 1;
            if (((temp_v0_6 == 0) || (e->bytes[2] = temp_v0_7, ((temp_v0_7 & 0xFF) == 0))) && (e->on_ground != 0) && (sp2C < 2U) && (sp30 < 0)) {
                e->target_anim = 4;
                return;
            }
            temp_v1_5 = e->bytes[0];
            if (temp_v1_5 == 1) {
                if (e->bytes[1] == 0) {
                    temp_v0_8 = (*(void *)0x801247C0 - 3) << 7;
                    *(void *)0x801247B4 = temp_v0_8;
                    *(void *)0x801247B0 = temp_v0_8;
                    e->bytes[1] = 1;
                    temp_a1_2 = *(void *)0x801247C0 * 8;
                    *(void *)0x801247A8 = (s32) ((e->px - *(&D_80027C3C + temp_a1_2)) + 0x01500000);
                    *(void *)0x801247AC = (s32) ((e->py - *(&D_80027C40 + temp_a1_2)) + 0x03100000);
                }
                temp_v0_9 = (*(void *)0x801247B0 + 2) & 0x1FF;
                *(void *)0x801247B0 = temp_v0_9;
                if (temp_v0_9 == *(void *)0x801247B4) {
                    e->bytes[0] = 0;
                    e->target_anim = 2;
                }
                temp_a0_2 = *(void *)0x801247B0 * 2;
                e->px = *(void *)0x801247A8 + (*(&D_800282D8 + temp_a0_2) * 0x3000);
                e->py = *(void *)0x801247AC - (*(&D_800286D8 + temp_a0_2) * 0x3000);
                return;
            }
            if (temp_v1_5 == 2) {
                temp_v1_6 = e->bytes[1];
                switch (temp_v1_6) {                /* switch 2 */
                case 0:                             /* switch 2 */
                    e->bytes[1] = *(void *)0x801247C0 + 1;
                    temp_a0_3 = *(void *)0x801247C0;
                    temp_a1_3 = temp_a0_3 * 8;
                    *(void *)0x801247AC = (s32) ((e->py - *(&D_80027C40 + temp_a1_3)) + 0x02C00000);
                    if (temp_a0_3 == 0) {
                        var_a0_2 = D_80027C3C;
                        *(void *)0x801247B0 = 0x180;
                        var_v0 = 0x01080000;
                    } else {
                        var_v0_2 = 0x80;
                        if (temp_a0_3 == 1) {
                            var_a0_2 = D_80027C44;
                            var_v0_2 = 0x180;
                        } else {
                            var_a0_2 = *(&D_80027C3C + temp_a1_3);
                        }
                        *(void *)0x801247B0 = var_v0_2;
                        var_v0 = 0x01980000;
                    }
                    *(void *)0x801247A8 = (s32) ((e->px - var_a0_2) + var_v0);
                    break;
                case 1:                             /* switch 2 */
                    temp_v0_10 = (*(void *)0x801247B0 + 4) & 0x1FF;
                    *(void *)0x801247B0 = temp_v0_10;
                    if (temp_v0_10 == 0x80) {
                        if (*(void *)0x801247C0 == 1) {
                            e->bytes[0] = 0x80;
                        }
                        *(void *)0x801247B0 = 0x180;
                        *(void *)0x801247A8 = (s32) (*(void *)0x801247A8 + 0x900000);
                        var_v0_3 = 2;
block_75:
                        e->bytes[1] = var_v0_3;
                    }
                    break;
                case 2:                             /* switch 2 */
                    temp_v0_11 = (*(void *)0x801247B0 - 4) & 0x1FF;
                    *(void *)0x801247B0 = temp_v0_11;
                    if (temp_v0_11 == 0x80) {
                        if (*(void *)0x801247C0 == 2) {
                            e->bytes[0] = 0x80;
                        }
                        var_v0_3 = 3;
                        goto block_75;
                    }
                    break;
                case 3:                             /* switch 2 */
                    temp_v0_12 = (*(void *)0x801247B0 - 4) & 0x1FF;
                    *(void *)0x801247B0 = temp_v0_12;
                    if (temp_v0_12 == 0x180) {
                        *(void *)0x801247B0 = 0x80;
                        *(void *)0x801247A8 = (s32) (*(void *)0x801247A8 + 0xFF700000);
                        var_v0_3 = 4;
                        goto block_75;
                    }
                    break;
                case 4:                             /* switch 2 */
                    temp_v0_13 = (*(void *)0x801247B0 + 4) & 0x1FF;
                    *(void *)0x801247B0 = temp_v0_13;
                    if (temp_v0_13 == 0x180) {
                        var_v0_3 = 1;
                        if (*(void *)0x801247C0 == 0) {
                            e->bytes[0] = 0x80;
                            var_v0_3 = 1;
                        }
                        goto block_75;
                    }
                    break;
                }
                temp_a0_4 = *(void *)0x801247B0 * 2;
                e->px = *(void *)0x801247A8 + (*(&D_800282D8 + temp_a0_4) * 0x1800);
                e->py = *(void *)0x801247AC - (*(&D_800286D8 + temp_a0_4) * 0x1800);
                if (e->bytes[0] == 0x80) {
                    e->bytes[0] = 0;
                    e->target_anim = 2;
                    return;
                }
            } else {
                e->bytes[0] = 0;
                if ((u16) e->ai[4] != 0) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo + 0xE06A02E7;
                    var_s1 = (temp_lo + 0xE06A02E7) / 1073741824;
                } else {
                    var_s1 = 4;
                }
                switch (var_s1) {                   /* switch 3 */
                case 0:                             /* switch 3 */
                case 3:                             /* switch 3 */
                    e->bytes[0] = 4;
                    e->bytes[1] = 5;
                    e->target_anim = 1;
                    e->ai[4] = (u16) e->ai[4] - 1;
                    var_a0_3 = g_ent->px - e->px;
block_104:
                    var_v0_4 = dir_from_delta(var_a0_3, g_ent->py - e->py);
block_105:
                    e->target_dir = var_v0_4;
                    e->ai[1] = 0x3C;
                    return;
                case 1:                             /* switch 3 */
                    e->bytes[0] = 3;
                    e->bytes[1] = 5;
                    e->ai[4] = (u16) e->ai[4] - 1;
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    e->target_anim = 1;
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    e->ai[1] = 0x3C;
                    e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
                    return;
                case 2:                             /* switch 3 */
                    e->bytes[0] = 8;
                    e->target_anim = 1;
                    e->ai[4] = (u16) e->ai[4] - 1;
                    *(void *)0x801247C0 = 3;
                    return;
                case 4:                             /* switch 3 */
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    e->target_anim = 2;
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    e->bytes[0] = 5;
                    e->ai[4] = ((temp_lo_3 + 0xE06A02E7) / MULHI_3) + 2;
                    return;
                default:                            /* switch 1 */
                default:                            /* switch 3 */
                    return;
                }
            }
        }
        break;
    case 1:                                         /* switch 1 */
        temp_a2 = e->bytes[0];
        if ((temp_a2 == 5) || (temp_a2 == 8)) {
            temp_v0_14 = *(void *)0x801247C0 * 8;
            temp_a3_2 = e->px - *(&D_80027C3C + temp_v0_14);
            temp_t1_2 = e->py - *(&D_80027C40 + temp_v0_14);
            var_v0_5 = temp_a3_2;
            if (temp_a3_2 < 0) {
                var_v0_5 = -var_v0_5;
            }
            if (var_v0_5 <= 0x60000) {
                var_v0_6 = temp_t1_2;
                if (temp_t1_2 < 0) {
                    var_v0_6 = -var_v0_6;
                }
                if (var_v0_6 > 0x60000) {
                    goto block_95;
                }
                if (temp_a2 == 5) {
                    e->target_anim = 3;
                    return;
                }
block_161:
                e->target_anim = 2;
                return;
            }
block_95:
            e->target_dir = dir_from_delta(-temp_a3_2, -temp_t1_2);
            return;
        }
        temp_v0_15 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_15;
        if (!(temp_v0_15 & 0xFFFF)) {
            temp_v0_16 = e->bytes[1] - 1;
            e->bytes[1] = temp_v0_16;
            if (!(temp_v0_16 & 0xFF)) {
                e->target_anim = 0;
                e->ai[1] = 0x3C;
                goto block_186;
            }
            if (e->bytes[0] == 3) {
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                var_v0_4 = (temp_lo_4 + 0xE06A02E7) / 134217728;
            } else {
                var_a0_3 = g_ent->px - e->px;
                goto block_104;
            }
            goto block_105;
        }
        if ((e->force_adjusted != 0) || ((u32) (e->px + 0xFF700000) > 0x01680000U) || ((u32) (e->py + 0xFD900000) > 0x01300000U)) {
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
            return;
        }
        if (sp20 < 3) {
            if (sp24 < 3) {
                e->target_anim = 0xA;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->flags |= 0x100;
                return;
            }
            goto block_114;
        }
block_114:
        if ((e->py <= 0x035FFFFF) && (sees_player_q(e, &sp20, 0, 3, 5, 0x500000) != 0)) {
            e->bytes[0] = 6;
            e->item_state = 0;
            e->target_anim = 4;
            temp_v0_17 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            *(void *)0x801247C4 = temp_v0_17;
            e->target_dir = temp_v0_17;
            return;
        }
        break;
    case 3:                                         /* switch 1 */
        if (e->bytes[0] == 8) {
            temp_v1_7 = e->item_state;
            if (temp_v1_7 >= 8) {
                temp_lo_5 = (s32) (sp24 << 0x14) / temp_v1_7;
                temp_lo_6 = (s32) (sp20 * 0x180000) / (s32) e->item_state;
                *(void *)0x801247CC = temp_lo_5;
                *(void *)0x801247C8 = temp_lo_6;
                if ((s32) sp2C >= 0) {
                    *(void *)0x801247C8 = (s32) -temp_lo_6;
                }
                if (sp30 >= 0) {
                    *(void *)0x801247CC = (s32) -temp_lo_5;
                }
                e->item_state -= 1;
            }
            temp_v0_18 = e->mpx;
            if (((temp_v0_18 + 0xFFFF0000) <= 0x900000) || ((temp_v0_18 + e->sizex + 0x10001) > 0x020FFFFF)) {
                *(void *)0x801247C8 = 0;
            } else {
                temp_v0_19 = e->mpy;
                if (((temp_v0_19 + 0xFFFF0000) <= 0x02700000) || ((temp_v0_19 + e->sizey + 0x10001) > 0x03AFFFFF)) {
                    *(void *)0x801247CC = 0;
                }
            }
            e->pafx = *(void *)0x801247C8;
            e->pafy = *(void *)0x801247CC;
        }
        if (((u16) e->ai[1] == 0) && ((e->pz - e->terrain) <= 0x200000)) {
            e->ai[1] = 1;
            e->fz = (s32) e->fz >> 1;
            if (e->bytes[0] == 8) {
                e->flags &= ~0x100;
            }
        }
        if (e->on_ground != 0) {
            e->ai[1] = 0;
            e->target_anim = 0;
            if (e->bytes[0] == 5) {
                e->bytes[1] = 0;
                var_v0_7 = 2;
                if (*(void *)0x801247C0 >= 3) {
                    var_v0_7 = 1;
                }
                e->bytes[0] = var_v0_7;
            }
            if (e->bytes[0] == 8) {
                *(void *)0x801247CC = 0;
                *(void *)0x801247C8 = 0;
                e->ai[1] = 0x1E;
                *(void *)0x801247D0 = 0x14;
                *(void *)0x801F94D0 = 1;
                *(s32 *)0x801F94DC = 1;
                *(s32 *)0x801F94E0 = 1;
                *(s32 *)0x801F94D4 = 2;
                *(s32 *)0x801F94D8 = 2;
                return;
            }
        }
        break;
    case 10:                                        /* switch 1 */
        if (e->on_ground != 0) {
            e->ai[1] = 0;
            temp_lo_7 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_7 + 0xE06A02E7;
            e->flags &= ~0x100;
            if (((temp_lo_7 + 0xE06A02E7) / MULHI_3) == 0) {
                e->target_anim = 9;
                return;
            }
            goto block_161;
        }
        break;
    case 2:                                         /* switch 1 */
        temp_a0_5 = e->pz - e->terrain;
        e->ai[1] = ((u16) e->ai[1] + 1) & 0xF;
        if (e->bytes[0] != 8) {
            if (temp_a0_5 <= 0x3FFFFF) {
                goto block_154;
            }
            goto block_149;
        }
        if (temp_a0_5 > 0x9FFFFF) {
block_149:
            temp_v1_8 = e->bytes[0];
            e->fz = 0;
            e->flags &= ~0x100;
            if (temp_v1_8 == 5) {
                temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 1;
                g_rng_seed = temp_lo_8 + 0xE06A02E7;
                *(void *)0x801247C0 = (s32) ((temp_lo_8 + 0xE06A02E7) / MULHI_7);
                return;
            }
            if (temp_v1_8 == 8) {
                play_sound(0x63);
                e->ai[1] = 0x28;
                e->target_anim = 0;
                return;
            }
            e->target_anim = 0;
            e->ai[1] = 0x3C;
            return;
        }
block_154:
        if ((temp_a0_5 > 0x2FFFFF) || ((u16) e->ai[1] != 0) || (e->bytes[0] == 7)) {
            e->flags &= ~0x100;
            return;
        }
        goto block_159;
    case 9:                                         /* switch 1 */
        if (e->anim_done != 0) {
            goto block_161;
        }
        break;
    case 4:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 5;
            if (e->on_ground != 0) {
                e->ai[1] = 1;
                e->bytes[2] = 0;
                return;
            }
            play_sound(0x62);
            *(void *)0x801247D4 = spawn_warp_entity(e, 1, 0xE0, e->px + 0xFFE20000, /* extra? */ (e->py + 0x1A0000), /* extra? */ (e->pz + 0xFFC40000), /* extra? */ 0);
            e->ai[1] = 0xF0;
            return;
        }
        break;
    case 5:                                         /* switch 1 */
        temp_v0_20 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_20;
        if (!(temp_v0_20 & 0xFFFF)) {
            if (e->on_ground != 0) {
                play_sound(0x61);
                var_s1_2 = 0x1D;
                do {
                    temp_v0_21 = spawn_warp_entity(e, 1, 0xE1, e->px + 0xFFE40000, /* extra? */ (e->py + 0x200000), /* extra? */ (e->pz + 0x100000), /* extra? */ var_s1_2);
                    var_v0_8 = var_s1_2 + 1;
                    if (temp_v0_21 != NULL) {
                        temp_v0_21->target_anim = 1;
                        var_v0_8 = var_s1_2 + 1;
                    }
                    var_s1_2 = var_v0_8 & 0x1F;
                } while (var_s1_2 != 4);
                e->ai[1] = 0x19;
                temp_v0_22 = e->bytes[2] + 1;
                e->bytes[2] = temp_v0_22;
                if ((temp_v0_22 & 0xFF) == 3) {
                    e->target_anim = 6;
                    return;
                }
            } else {
                func_8004A7B4(0x62);
                temp_a0_6 = *(void *)0x801247D4;
                e->target_anim = 6;
                temp_v0_23 = temp_a0_6->flags;
                *(void *)0x801247D4 = NULL;
                temp_a0_6->target_anim = 2;
                temp_a0_6->flags = temp_v0_23 | 0x40;
                return;
            }
        }
        break;
    case 6:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 0;
            if (e->on_ground != 0) {
                e->bytes[2] = 0x28;
                return;
            }
            goto block_186;
        }
        break;
    case 7:                                         /* switch 1 */
        if (*(void *)0x801247D4 != NULL) {
            func_8004A7B4(0x62);
            temp_v0_24 = *(void *)0x801247D4;
            temp_v1_9 = temp_v0_24->flags;
            *(void *)0x801247D4 = NULL;
            temp_v0_24->target_anim = 2;
            temp_v0_24->flags = temp_v1_9 | 0x40;
        }
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                *(void *)0x801F94D0 = 0;
                e->fz = 0;
                return;
            }
            e->damaged_tick = 0x5A;
            if ((u32) (e->bytes[0] - 1) < 2U) {
                e->target_anim = 0;
                e->bytes[2] = 0x28;
                return;
            }
            goto block_185;
        }
        break;
    }
}
