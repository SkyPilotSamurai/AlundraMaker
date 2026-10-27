/* 80074160: built-in program C44 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_800832B0();                                  /* extern */
extern ? D_80023654;
extern ? D_80023694;
extern ? D_8002784C;
extern ? D_80027850;
extern ? D_80027874;
extern ? D_80027878;
extern ? D_8002787C;

void AI_C44(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 temp_v0_10;
    s16 temp_v0_11;
    s16 temp_v0_13;
    s16 temp_v0_16;
    s16 temp_v0_8;
    s32 temp_a0;
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
    s32 temp_v0_3;
    s32 temp_v0_4;
    s32 temp_v0_5;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_a0;
    s32 var_a1;
    s32 var_s1;
    s32 var_s3;
    s32 var_v0;
    struct Entity *temp_v0_14;
    struct Entity *temp_v0_6;
    u16 temp_v0_12;
    u16 temp_v0_15;
    u16 temp_v0_7;
    u16 temp_v0_9;
    u32 temp_a1;
    u32 temp_a1_2;
    u32 temp_a3;
    u32 temp_t0;
    u8 temp_v0_2;
    u8 temp_v1_3;
    u8 var_v0_2;

    if (!(*(s32 *)0x801E6378 & 1)) {
        if ((u8) e->bytes[2] < 5U) {
            temp_v0 = e->delay + 1;
            e->delay = temp_v0;
            if (temp_v0 == 0x12C) {
                temp_v1 = e->bytes[1] * 8;
                spawn_warp_entity(e, 1, 0xFF, *(&D_8002784C + temp_v1), /* extra? */ *(&D_80027850 + temp_v1), /* extra? */ 0x01500000, /* extra? */ 0)->target_anim = 4;
                e->delay = 0;
                temp_v0_2 = e->bytes[1] + 1;
                e->bytes[1] = temp_v0_2;
                e->bytes[2] += 1;
                if ((u32) (temp_v0_2 & 0xFF) >= 5U) {
                    e->bytes[1] = 0;
                }
            }
        }
        temp_v0_3 = e->item_state;
        temp_v0_4 = temp_v0_3 - 1;
        if (temp_v0_3 != 0) {
            e->item_state = temp_v0_4;
            if (!(temp_v0_4 & 0xF)) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                temp_t0 = temp_lo + 0xE06A02E7;
                sp38 = temp_t0 * 0x20;
                sp3C = (temp_lo + 0xE06A02E7) / 134217728;
                temp_v0_5 = ((temp_lo + 0xE06A02E7) / 134217728) * 2;
                temp_a0 = (*(s32 *)0x80124784 << 6) + 0xA00;
                temp_lo_2 = temp_t0 * 0x7D2B89DD;
                temp_a3 = temp_lo_2 + 0xE06A02E7;
                g_rng_seed = temp_t0;
                g_rng_seed = temp_a3;
                sp38 = temp_a3 * 0x20;
                sp3C = (temp_lo_2 + 0xE06A02E7) / 134217728;
                temp_v0_6 = spawn_warp_entity(e, 1, 0xD5, e->px + (*(&D_80023654 + temp_v0_5) * temp_a0), /* extra? */ (e->py + (*(&D_80023694 + temp_v0_5) * temp_a0)), /* extra? */ (e->pz + 0x01000000), /* extra? */ ((temp_lo_2 + 0xE06A02E7) / 134217728));
                if (temp_v0_6 != NULL) {
                    if ((e->pz + 0x01000000) < temp_v0_6->terrain) {
                        remove_entity(temp_v0_6);
                    } else {
                        play_sound(0xB7);
                        temp_v0_6->fz = -0x80000;
                    }
                }
                *(void *)0x80124784 = (s32) (*(void *)0x80124784 + 8);
            }
        }
        rel_tile_z(e, &sp20);
        temp_v1_2 = e->target_anim;
        switch (temp_v1_2) {
        case 0:
            temp_v0_7 = (u16) e->ai[1];
            temp_v0_8 = temp_v0_7 - 1;
            if ((temp_v0_7 == 0) || (e->ai[1] = temp_v0_8, ((temp_v0_8 & 0xFFFF) == 0))) {
                if ((sp20 >= 3) || (sp24 >= 3) || (sp28 > 0x200000)) {
                    if ((sp20 < 6) && (sp24 < 6) && (sp28 <= 0x200000)) {
                        e->target_anim = 3;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->ai[1] = 0x3A;
                        return;
                    }
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    if ((((temp_lo_3 + 0xE06A02E7) / MULHI_3) == 0) && (e->item_state == 0)) {
                        e->target_anim = 4;
block_46:
                        var_v0 = g_ent->py;
                        var_a1 = e->py;
                        var_a0 = g_ent->px - e->px;
block_47:
                        e->target_dir = dir_from_delta(var_a0, var_v0 - var_a1);
                        return;
                    }
                    goto block_69;
                }
block_69:
                e->target_anim = 6;
                return;
            }
            break;
        case 2:
            temp_v0_9 = (u16) e->ai[1];
            temp_v0_10 = temp_v0_9 - 1;
            if ((temp_v0_9 == 0) || (e->ai[1] = temp_v0_10, ((temp_v0_10 & 0xFFFF) == 0))) {
                if ((sp20 < 6) && (sp24 < 6) && (sp34 <= 0x600000U)) {
                    e->bytes[0] = 3;
                    e->target_anim = 1;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->ai[1] = 0x3C;
                } else {
                    e->bytes[0] = 0;
                    start_moving_half(e, 1, 0x3C);
                }
                if ((e->pz - e->terrain) > 0x600000) {
                    e->bytes[0] = 1;
                    return;
                }
            }
            break;
        case 1:
            temp_v1_3 = e->bytes[0];
            temp_v0_11 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_11;
            if (temp_v1_3 != 0) {
                var_v0_2 = temp_v1_3 - 1;
                if (!(temp_v0_11 & 0xFFFF) || (var_v0_2 = temp_v1_3 - 1, (e->force_adjusted != 0))) {
                    e->bytes[0] = var_v0_2;
                    if (!(var_v0_2 & 0xFF)) {
                        temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                        e->target_anim = 7;
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        if (((temp_lo_4 + 0xE06A02E7) / MULHI_3) != 0) {
                            var_v0 = e->py;
                            var_a1 = g_ent->py;
                            var_a0 = e->px - g_ent->px;
                            goto block_47;
                        }
                    } else {
                        start_moving(e, 1, 0x32, 0x32);
                        return;
                    }
                } else if ((sp20 < 4) && (sp24 < 4)) {
                    temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                    temp_a1 = temp_lo_5 + 0xE06A02E7;
                    e->target_anim = 7;
                    g_rng_seed = temp_a1;
                    temp_lo_6 = temp_a1 * 0x7D2B89DD;
                    if (((temp_lo_5 + 0xE06A02E7) / MULHI_3) == 0) {
                        goto block_46;
                    }
                    g_rng_seed = temp_lo_6 + 0xE06A02E7;
                    e->target_dir = (temp_lo_6 + 0xE06A02E7) / 134217728;
                    return;
                }
            } else if (!(temp_v0_11 & 0xFFFF) || (e->force_adjusted != 0)) {
                temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                temp_a1_2 = temp_lo_7 + 0xE06A02E7;
                g_rng_seed = temp_a1_2;
                temp_lo_8 = temp_a1_2 * 0x7D2B89DD;
                if (((temp_lo_7 + 0xE06A02E7) / 1073741824) == 0) {
                    e->target_anim = 7;
                    return;
                }
                e->target_dir = 0;
                e->target_anim = 2;
                g_rng_seed = temp_lo_8 + 0xE06A02E7;
                e->ai[1] = ((temp_lo_8 + 0xE06A02E7) / 268435456) + 0x1E;
                return;
            }
            break;
        case 6:
            if ((e->pz - e->terrain) > 0x4FFFFF) {
                temp_lo_9 = g_rng_seed * 0x7D2B89DD;
                e->fz = 0;
                e->target_anim = 2;
                g_rng_seed = temp_lo_9 + 0xE06A02E7;
                e->ai[1] = ((temp_lo_9 + 0xE06A02E7) / 268435456) + 0x3C;
                return;
            }
            break;
        case 7:
            if (e->on_ground != 0) {
                e->fz = 0;
                e->target_anim = 0;
                e->ai[1] = 0xF;
                return;
            }
            break;
        case 3:
            temp_v0_12 = (u16) e->ai[1];
            temp_v0_13 = temp_v0_12 - 1;
            if (temp_v0_12 != 0) {
                e->ai[1] = temp_v0_13;
                if (!(temp_v0_13 & 0xFFFF)) {
                    play_sound(0xB9);
                    temp_lo_10 = g_rng_seed * 0x7D2B89DD;
                    var_s3 = 0;
                    g_rng_seed = temp_lo_10 + 0xE06A02E7;
                    var_s1 = ((temp_lo_10 + 0xE06A02E7) / MULHI_3) * 0x6C;
                    do {
                        var_s3 += 1;
                        temp_v0_14 = spawn_warp_entity(e, 1, 0xFE, g_ent->px + *(&D_80027874 + var_s1), /* extra? */ (g_ent->py + *(&D_80027878 + var_s1)), /* extra? */ g_ent->terrain, /* extra? */ 0);
                        temp_v0_14->target_anim = 4;
                        temp_v0_14->ai[1] = (s16) *(&D_8002787C + var_s1);
                        var_s1 += 0xC;
                    } while (var_s3 != 9);
                }
            }
block_68:
            if (e->anim_done != 0) {
                goto block_69;
            }
            break;
        case 4:
            if (e->anim_done != 0) {
                e->target_anim = 5;
                e->ai[1] = 0x1C;
                return;
            }
            break;
        case 5:
            temp_v0_15 = (u16) e->ai[1];
            temp_v0_16 = temp_v0_15 - 1;
            if (temp_v0_15 != 0) {
                e->ai[1] = temp_v0_16;
                if (!(temp_v0_16 & 0xFFFF)) {
                    e->item_state = 0x100;
                    *(void *)0x80124784 = 0;
                    func_800832B0();
                }
            }
            goto block_68;
        case 9:
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 1);
                    e->target_anim = 0;
                    e->fz = 0;
                    return;
                }
                e->target_anim = 6;
                e->damaged_tick = 0x5A;
            }
            break;
        }
    } else {
    default:
    }
}
