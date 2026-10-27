/* 80071080: built-in program C38 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
? func_80083394();                                  /* extern */
extern ? D_80027600;
extern s16 D_800282D8;
extern ? D_800286D8;

void AI_C38(struct Entity *e) {
    s32 sp20;
    s32 sp24;
    s16 *var_s3_2;
    s16 temp_s2;
    s16 temp_v0_12;
    s16 temp_v0_17;
    s16 temp_v0_2;
    s16 var_s3;
    s16 var_v0;
    s32 temp_a0;
    s32 temp_a0_4;
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
    s32 temp_t4;
    s32 temp_t5;
    s32 temp_v0_5;
    s32 temp_v1_2;
    s32 temp_v1_6;
    s32 var_s1;
    s32 var_s1_2;
    s32 var_s1_3;
    s32 var_s1_4;
    s32 var_s1_5;
    s32 var_s1_6;
    s32 var_s2;
    s32 var_s2_2;
    s32 var_s2_3;
    s32 var_s3_3;
    s32 var_t4;
    s32 var_t4_2;
    s32 var_t5;
    s32 var_t5_2;
    s32 var_t5_3;
    s32 var_v0_2;
    s32 var_v0_4;
    s32 var_v1;
    struct Entity *temp_v0_10;
    struct Entity *temp_v0_13;
    struct Entity *temp_v0_16;
    struct Entity *temp_v0_6;
    struct Entity *temp_v0_7;
    struct Entity *temp_v0_9;
    u16 temp_v0;
    u16 temp_v0_11;
    u16 temp_v0_14;
    u16 temp_v0_4;
    u16 temp_v0_8;
    u32 temp_a0_2;
    u32 temp_t1;
    u32 temp_v0_15;
    u32 temp_v1_5;
    u8 temp_a0_3;
    u8 temp_v0_3;
    u8 temp_v1;
    u8 temp_v1_3;
    u8 temp_v1_4;
    void *var_v0_3;

    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394();
            return;
        }
        e->target_anim = 7;
        e->flags |= 0x40;
        return;
    }
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {                            /* switch 1 */
    case 8:                                         /* switch 1 */
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if ((temp_v0 == 0) || (e->ai[1] = temp_v0_2, ((temp_v0_2 & 0xFFFF) == 0))) {
            temp_v1_3 = e->bytes[2];
            switch (temp_v1_3) {                    /* switch 2 */
            case 0:                                 /* switch 2 */
                e->bytes[2] = 1;
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[1] = 0x3C;
                e->bytes[1] = ((temp_lo + 0xE06A02E7) / MULHI_3) + 1;
                return;
            case 1:                                 /* switch 2 */
                temp_v0_3 = e->bytes[1];
                if (temp_v0_3 == 0) {
                    temp_v1_4 = e->bytes[0];
                    temp_a0 = temp_v1_4 & 0xFF;
                    if ((temp_a0 == 3) || ((u32) (temp_v1_4 - 5) < 2U) || (temp_a0 == 8)) {
                        temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_2 + 0xE06A02E7;
                        if (((temp_lo_2 + 0xE06A02E7) / MULHI_3) == 0) {
                            e->bytes[2] = 5;
                            return;
                        }
                    }
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    temp_a0_2 = (temp_lo_3 + 0xE06A02E7) / 536870912;
                    switch (temp_a0_2) {            /* switch 3 */
                    case 0:                         /* switch 3 */
                    case 2:                         /* switch 3 */
                    case 4:                         /* switch 3 */
                        e->bytes[2] = 2;
                        e->ai[4] = 8;
                        temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        e->delay = (temp_lo_4 + 0xE06A02E7) / 134217728;
                        return;
                    case 6:                         /* switch 3 */
                    case 7:                         /* switch 3 */
                        e->bytes[2] = 3;
                        return;
                    case 1:                         /* switch 3 */
                    case 3:                         /* switch 3 */
                    case 5:                         /* switch 3 */
                        e->bytes[2] = 4;
                        return;
                    }
                } else {
                    e->bytes[1] = temp_v0_3 - 1;
                    e->bytes[2] = 1;
                    e->ai[1] = 0x40;
                    temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                    e->target_anim = 4;
                    g_rng_seed = temp_lo_5 + 0xE06A02E7;
                    var_s1 = (temp_lo_5 + 0xE06A02E7) / 1073741824;
                    do {
                        temp_s2 = *((var_s1 * 2) + ((e->bytes[0] * 8) + &D_80027600));
                        var_s1 = (var_s1 + 1) & 3;
                    } while (e->target_dir == temp_s2);
                    e->target_dir = (s32) temp_s2;
                    switch (temp_s2) {              /* switch 4; irregular */
                    case 4:                         /* switch 4 */
                        e->bytes[0] -= 3;
                        return;
                    case 12:                        /* switch 4 */
                        e->bytes[0] += 2;
                        return;
                    case 20:                        /* switch 4 */
                        e->bytes[0] += 3;
                        return;
                    default:                        /* switch 4 */
                        e->bytes[0] -= 2;
                        return;
                    }
                }
                break;
            case 2:                                 /* switch 2 */
                temp_v0_4 = (u16) e->ai[4];
                if (temp_v0_4 == 0) {
                    e->bytes[2] = 0;
                    return;
                }
                var_s2 = 0;
                var_s1_2 = e->delay;
                var_s3 = 0;
                e->ai[4] = temp_v0_4 - 1;
                e->ai[1] = 0xC;
                e->delay = (var_s1_2 + 2) & 0x1F;
                play_sound(0xBE);
                do {
                    temp_v0_5 = ((var_s1_2 ^ 0x1F) + 1) << 5;
                    temp_v0_6 = spawn_warp_entity(e, 1, 0xE4, e->px + (*(temp_v0_5 + &D_800282D8) << 0xB), /* extra? */ (e->py + (*(&D_800286D8 + temp_v0_5) << 0xB)), /* extra? */ e->pz, /* extra? */ var_s1_2);
                    if (temp_v0_6 != NULL) {
                        temp_v0_6->target_anim = 3;
                        temp_v0_6->ai[1] = var_s3;
                    }
                    var_s1_2 = (var_s1_2 + 8) & 0x1F;
                    var_s2 += 1;
                    var_s3 += 3;
                } while (var_s2 != 4);
                return;
            case 3:                                 /* switch 2 */
                e->target_anim = 2;
                var_v0 = 0x14;
block_110:
                e->ai[1] = var_v0;
                break;
            case 4:                                 /* switch 2 */
                e->target_anim = 2;
                return;
            case 5:                                 /* switch 2 */
                var_s2_2 = 0;
                var_s1_3 = 0;
                var_s3_2 = &D_800282D8;
                e->target_anim = 2;
                e->ai[1] = 0x78;
                do {
                    temp_v0_7 = spawn_warp_entity(e, 1, (var_s1_3 & 1) | 0xE6, e->px + (*var_s3_2 << 0xC), /* extra? */ (e->py + (*(&D_800286D8 + (var_s1_3 << 7)) << 0xC)), /* extra? */ e->pz, /* extra? */ var_s2_2);
                    if (temp_v0_7 != NULL) {
                        temp_v0_7->target_anim = 2;
                        temp_v0_7->bytes[2] = 5;
                        temp_v0_7->ai[1] = 0x5A;
                    }
                    var_s2_2 = (var_s2_2 - 4) & 0x1F;
                    var_s1_3 += 1;
                    var_s3_2 += 0x80;
                } while (var_s1_3 != 8);
                return;
            }
        } else {
        default:                                    /* switch 1 */
        default:                                    /* switch 2 */
        default:                                    /* switch 3 */
            return;
        }
        break;
    case 4:                                         /* switch 1 */
        temp_v0_8 = (u16) e->ai[1];
        if (temp_v0_8 != 0) {
            e->ai[1] = temp_v0_8 - 1;
        }
        if (!((u16) e->ai[1] & 7)) {
            temp_v0_9 = spawn_warp_entity(e, 1, 0xE4, e->px, /* extra? */ (e->py + 0xFFFF0000), /* extra? */ e->pz, /* extra? */ 0);
            if (temp_v0_9 != NULL) {
                temp_v0_9->target_anim = 2;
                temp_v0_9->flags = (temp_v0_9->flags & ~3) | 0x40;
            }
        }
        if (!((u16) e->ai[1] & 0x3F)) {
            temp_lo_6 = g_rng_seed * 0x7D2B89DD;
            temp_v1_5 = temp_lo_6 + 0xE06A02E7;
            temp_lo_7 = temp_v1_5 * 0x7D2B89DD;
            sp20 = temp_v1_5 * 0xD;
            sp24 = (temp_lo_6 + 0xE06A02E7) / MULHI_13;
            g_rng_seed = temp_v1_5;
            g_rng_seed = temp_lo_7 + 0xE06A02E7;
            var_t5 = g_ent->px + (((temp_lo_6 + 0xE06A02E7) / MULHI_13) << 0x13) + 0xFFD00000;
            var_t4 = g_ent->py + (((temp_lo_7 + 0xE06A02E7) / MULHI_17) << 0x12) + 0xFFE00000;
            if (var_t5 <= 0x0137FFFF) {
                var_t5 = 0x012C0000;
            }
            if (var_t5 > 0x02580000) {
                var_t5 = 0x02640000;
            }
            if (var_t4 <= 0x017FFFFF) {
                var_t4 = 0x01780000;
            }
            if (var_t4 > 0x02500000) {
                var_t4 = 0x02580000;
            }
            temp_v0_10 = spawn_warp_entity(e, 1, 0xE6, var_t5, /* extra? */ var_t4, /* extra? */ g_ent->pz, /* extra? */ 0);
            if (temp_v0_10 != NULL) {
                temp_v0_10->target_anim = 2;
                temp_v0_10->bytes[2] = 1;
            }
        }
        if ((u16) e->ai[1] == 0) {
            e->target_anim = 8;
            e->ai[1] = 0x28;
            e->target_dir = (e->target_dir + 0x10) & 0x1F;
            return;
        }
        break;
    case 2:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 0;
            return;
        }
        break;
    case 0:                                         /* switch 1 */
        temp_a0_3 = e->bytes[2];
        switch (temp_a0_3) {                        /* switch 5; irregular */
        case 3:                                     /* switch 5 */
            temp_v0_11 = (u16) e->ai[1];
            temp_v0_12 = temp_v0_11 - 1;
            if ((temp_v0_11 == 0) || (e->ai[1] = temp_v0_12, ((temp_v0_12 & 0xFFFF) == 0))) {
                e->ai[1] = 0xB4;
                var_s1_4 = 0;
                do {
                    (var_s1_4 + 0x80120000)->unk4760 = 0;
                    var_s1_4 += 1;
                } while (var_s1_4 != 0x24);
                var_s1_5 = 0;
loop_77:
                temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                temp_v1_6 = temp_lo_8 + 0xE06A02E7;
                temp_lo_9 = temp_v1_6 * 0x7D2B89DD;
                g_rng_seed = temp_lo_9 + 0xE06A02E7;
                sp20 = temp_v1_6 * 6;
                sp24 = (temp_lo_8 + 0xE06A02E7) / MULHI_6;
                var_t5_2 = (temp_lo_8 + 0xE06A02E7) / MULHI_6;
                var_t4_2 = (temp_lo_9 + 0xE06A02E7) / 1073741824;
                if (g_ent->py > 0x01F7FFFF) {
                    var_t4_2 += 2;
                }
                var_v1 = var_t4_2 * 6;
                var_v0_2 = var_t4_2 * 2;
                if (*(0x80124760 + (s32) (var_v1 + var_t5_2)) != 0) {
                    var_t5_3 = var_t5_2 + 2;
                    do {
                        var_v0_3 = var_v1 + var_t5_3;
                        if (var_t5_3 >= 6) {
                            var_t5_3 -= 6;
                            var_t4_2 += 1;
                            var_v1 += 6;
                            if (var_t4_2 >= 6) {
                                var_v1 = 0;
                                var_t4_2 = 0;
                            }
                            var_v0_3 = var_v1 + var_t5_3;
                        }
                        var_t5_3 += 2;
                    } while (*(0x80124760 + (s32) var_v0_3) != 0);
                    var_t5_2 = var_t5_3 - 2;
                    var_v0_2 = var_t4_2 * 2;
                }
                *(0x80124760 + (s32) (((var_v0_2 + var_t4_2) * 2) + var_t5_2)) = 1;
                temp_lo_10 = g_rng_seed * 0x7D2B89DD;
                temp_lo_11 = (temp_lo_10 + 0xE06A02E7) * 0x7D2B89DD;
                temp_t1 = temp_lo_11 + 0xE06A02E7;
                g_rng_seed = temp_t1;
                sp20 = temp_t1 * 0x15;
                sp24 = (temp_lo_11 + 0xE06A02E7) / MULHI_21;
                temp_v0_13 = spawn_warp_entity(e, 1, (var_s1_5 & 1) | 0xE6, (var_t5_2 * 0x300000) + ((((temp_lo_10 + 0xE06A02E7) / MULHI_25) << 0x10) + 0x01500000), /* extra? */ ((var_t4_2 * 0x280000) + ((((temp_lo_11 + 0xE06A02E7) / MULHI_21) << 0x10) + 0x01800000)), /* extra? */ e->pz, /* extra? */ 0);
                if (temp_v0_13 != NULL) {
                    temp_lo_12 = g_rng_seed * 0x7D2B89DD;
                    temp_v0_13->target_anim = 8;
                    g_rng_seed = temp_lo_12 + 0xE06A02E7;
                    temp_v0_13->bytes[2] = 3;
                    temp_v0_13->ai[1] = ((temp_lo_12 + 0xE06A02E7) / MULHI_31) + (var_s1_5 * 2) + 0xA;
                }
                var_s1_5 += 1;
                if (var_s1_5 != 0xC) {
                    goto loop_77;
                }
            }
            break;
        case 4:                                     /* switch 5 */
            temp_v0_14 = (u16) e->ai[1];
            var_v0 = temp_v0_14 - 1;
            if (temp_v0_14 == 0) {
                e->ai[1] = 0xC8;
                temp_v0_15 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                var_s1_6 = 0;
                var_s3_3 = 0xA;
                g_rng_seed = temp_v0_15;
                var_s2_3 = (((s32) MULTU_HI(temp_v0_15, temp_a0_3) >> 0) * 8) + 4;
                do {
                    temp_a0_4 = ((var_s2_3 ^ 0x1F) + 1) << 5;
                    temp_t5 = g_ent->px + (*(&D_800282D8 + temp_a0_4) * 0x1800);
                    temp_t4 = g_ent->py + (*(&D_800286D8 + temp_a0_4) * 0x1800);
                    var_v0_4 = var_s2_3 + 8;
                    if ((u32) (temp_t5 + 0xFEC80000) <= 0x01200000U) {
                        var_v0_4 = var_s2_3 + 8;
                        if ((u32) (temp_t4 + 0xFE800000) <= 0xD00000U) {
                            temp_v0_16 = spawn_warp_entity(e, 1, (var_s1_6 & 1) | 0xE6, temp_t5, /* extra? */ temp_t4, /* extra? */ g_ent->pz, /* extra? */ var_s2_3);
                            if (temp_v0_16 != NULL) {
                                temp_lo_13 = g_rng_seed * 0x7D2B89DD;
                                g_rng_seed = temp_lo_13 + 0xE06A02E7;
                                temp_v0_16->target_anim = 4;
                                temp_v0_16->delay = var_s3_3;
                                temp_v0_16->bytes[2] = 4;
                                temp_v0_16->ai[1] = ((temp_lo_13 + 0xE06A02E7) / MULHI_21) + 0x1E;
                                var_v0_4 = var_s2_3 + 8;
                                if (temp_v0_16->unk11E != e->unk11E) {
                                    remove_entity(temp_v0_16);
                                    goto block_98;
                                }
                            } else {
block_98:
                                var_v0_4 = var_s2_3 + 8;
                            }
                        }
                    }
                    var_s2_3 = var_v0_4 & 0x1F;
                    var_s1_6 += 1;
                    var_s3_3 += 0x1E;
                } while (var_s1_6 != 4);
                return;
            }
            goto block_110;
        case 5:                                     /* switch 5 */
            temp_v0_17 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_17;
            if (!(temp_v0_17 & 0xFFFF)) {
block_107:
                e->target_anim = 3;
                return;
            }
            break;
        }
        break;
    case 6:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                return;
            }
            goto block_107;
        }
        break;
    case 3:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 8;
            var_v0 = 0x3C;
            e->bytes[2] = 0;
            goto block_110;
        }
        break;
    }
}
