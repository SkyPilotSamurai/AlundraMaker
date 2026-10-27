/* 80069490: built-in program C7 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C7(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_10;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 temp_v0_8;
    s16 var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_s1;
    s32 temp_v0_6;
    s32 temp_v1;
    s32 var_hi;
    s32 var_s1;
    s32 var_s2;
    s32 var_v1;
    struct Entity *temp_v0_7;
    struct Entity *temp_v0_9;
    u16 temp_v0;
    u16 temp_v0_3;
    u8 temp_v0_5;
    u8 temp_v1_2;
    u8 temp_v1_3;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 2:                                         /* switch 1 */
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
        }
        if (e->bytes[1] == 0) {
            if ((sp20 < 3) && (sp24 < 3) && (sp28 <= 0)) {
                e->target_anim = 4;
                e->bytes[1] = 0xA;
                return;
            }
            if ((u16) e->ai[1] == 0) {
                e->target_anim = 4;
                e->bytes[1] = 0x14;
                return;
            }
        } else {
        default:                                    /* switch 1 */
        default:                                    /* switch 2 */
            return;
        }
        break;
    case 4:                                         /* switch 1 */
        if ((e->anim_done != 0) && ((temp_v1_2 = e->bytes[1], (temp_v1_2 == 0xA)) || (temp_v1_2 == 0x14))) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            var_hi = (temp_lo + 0xE06A02E7) / 268435456;
block_55:
            e->ai[1] = (var_hi >> 0) + 0x14;
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (temp_v0_2 & 0xFFFF) {
            if (e->force_adjusted != 0) {
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
            } else {
                temp_s1 = e->floor - g_ent->floor;
                if (temp_s1 >= 0) {
                    ledge_turn(e, 1, temp_s1);
                }
            }
            if ((e->bytes[1] != 0) && (sees_player(e, &sp20, 1, 2, 0) != 0)) {
block_30:
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->target_anim = 3;
                e->bytes[1] = 0;
                return;
            }
        } else {
            e->target_anim = 0;
            return;
        }
        break;
    case 0:                                         /* switch 1 */
        if (e->bytes[1] == 0) {
            e->bytes[1] = 0xA;
        }
        temp_v0_3 = (u16) e->ai[1];
        temp_v0_4 = temp_v0_3 - 1;
        if ((temp_v0_3 == 0) || (e->ai[1] = temp_v0_4, ((temp_v0_4 & 0xFFFF) == 0))) {
            if ((e->bytes[1] == 0xA) && (sees_player(e, &sp20, 1, 2, 0) != 0)) {
                goto block_30;
            }
            temp_v1_3 = e->bytes[1];
            if (((u32) (temp_v1_3 - 0xA) < 7U) || ((u32) (temp_v1_3 - 0x14) < 2U)) {
                if (sees_player(e, &sp20, 2, 6, 0) != 0) {
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->target_anim = 1;
                    e->ai[1] = 0x78;
                    return;
                }
                temp_v0_5 = e->bytes[1] + 1;
                e->bytes[1] = temp_v0_5;
                temp_v0_6 = temp_v0_5 & 0xFF;
                switch (temp_v0_6) {                /* switch 2 */
                case 11:                            /* switch 2 */
                case 14:                            /* switch 2 */
                    e->sfy = 0;
                    e->sfx = 0;
                    e->fy = 0;
                    e->fx = 0;
                    e->tfy = 0;
                    e->tfx = 0;
                    e->ai[1] = 0x28;
                    var_v1 = *(&D_80028AF8 + e->anim_quadrant) - 8;
block_39:
                    e->target_dir = var_v1 & 0x1F;
                    return;
                case 12:                            /* switch 2 */
                case 15:                            /* switch 2 */
                case 21:                            /* switch 2 */
                    e->sfy = 0;
                    e->sfx = 0;
                    e->fy = 0;
                    e->fx = 0;
                    e->tfy = 0;
                    e->tfx = 0;
                    e->ai[1] = 0x28;
                    var_v1 = *(&D_80028AF8 + e->anim_quadrant) + 0x10;
                    goto block_39;
                case 13:                            /* switch 2 */
                    start_moving(e, 1, 0x78, 0x1E);
                    return;
                case 16:                            /* switch 2 */
                case 22:                            /* switch 2 */
block_60:
                    e->target_anim = 5;
                    return;
                }
            }
        }
        break;
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 2;
            var_v0 = 0x78;
block_52:
            e->bytes[1] = 0;
            e->ai[1] = var_v0;
            return;
        }
        break;
    case 3:                                         /* switch 1 */
        if (g_ent->touching == e) {
            e->bytes[1] += 1;
        }
        if (e->anim_done != 0) {
            if (e->bytes[1] & 0xF) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                var_hi = (temp_lo_2 + 0xE06A02E7) / 536870912;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->target_anim = 0;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                goto block_54;
            }
            if (sees_player(e, &sp20, 1, 1, 0) != 0) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                if (e->bytes[1] == 0) {
                    e->target_anim = 3;
                    e->bytes[1] = 0x80;
                    return;
                }
                e->target_anim = 1;
                var_v0 = 0x14;
                goto block_52;
            }
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            var_hi = (temp_lo_3 + 0xE06A02E7) / 268435456;
            e->target_anim = 0;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
block_54:
            e->bytes[1] = 0xA;
            goto block_55;
        }
        break;
    case 7:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->ai[1] = 8;
                e->flags |= 0x40;
                return;
            }
            temp_lo_4 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_4 + 0xE06A02E7;
            if (((temp_lo_4 + 0xE06A02E7) / 1073741824) == 1) {
                goto block_60;
            }
            e->bytes[1] = 0;
            e->ai[1] = 0;
            temp_lo_5 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_5 + 0xE06A02E7;
            temp_v0_7 = spawn_warp_entity(e, 1, 0x91, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x100000), /* extra? */ (s32) *(((temp_lo_5 + 0xE06A02E7) / MULHI_5) + &D_80028AF8));
            if (temp_v0_7 != NULL) {
                temp_v0_7->bi_a = 0;
                temp_v0_7->target_anim = 0xB;
                temp_v0_7->contents_item = 0;
                return;
            }
        }
        break;
    case 8:                                         /* switch 1 */
        temp_v0_8 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_8;
        var_s1 = 0;
        if (!(temp_v0_8 & 0xFFFF)) {
            var_s2 = 4;
            do {
                temp_v0_9 = spawn_warp_entity(e, 1, 0x91, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x100000), /* extra? */ var_s2);
                if (temp_v0_9 != NULL) {
                    temp_v0_9->bi_a = 0;
                    temp_v0_9->target_anim = 0xB;
                    temp_v0_9->contents_item = 0;
                }
                var_s1 += 1;
                var_s2 += 8;
            } while (var_s1 != 4);
            return;
        }
        break;
    case 11:                                        /* switch 1 */
        if (e->on_ground != 0) {
            e->target_anim = 0xA;
            e->ai[1] = 0x3C;
            return;
        }
        break;
    case 10:                                        /* switch 1 */
        temp_v0_10 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_10;
        if (!(temp_v0_10 & 0xFFFF)) {
            play_sound(0x40);
            destroy_entity(e, -1);
        }
        break;
    }
}
