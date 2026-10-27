/* 80079E4C: built-in program C51 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
? func_80083394(void *, s32);                       /* extern */
extern ? D_80023654;
extern s16 D_80023664;
extern ? D_80023694;
extern ? D_80027E10;
extern ? D_80027E28;
extern ? D_80027E2C;
extern ? D_80027E30;
extern ? D_80027E70;
extern ? D_80027E74;
extern ? D_80027E90;
extern ? D_80027E94;
extern ? D_80028AF7;
extern ? D_80028AF8;

void AI_C51(struct Entity *e) {
    s32 sp20;
    s32 sp24;
    s16 temp_a1_4;
    s16 temp_v0_10;
    s16 temp_v0_12;
    s16 temp_v0_13;
    s16 temp_v0_14;
    s16 temp_v0_17;
    s16 temp_v0_21;
    s16 temp_v0_22;
    s16 temp_v0_23;
    s16 temp_v0_26;
    s16 temp_v0_5;
    s16 temp_v0_7;
    s16 temp_v0_8;
    s16 temp_v1_11;
    s16 temp_v1_3;
    s16 var_v0_3;
    s32 *temp_a0_4;
    s32 *var_v1_3;
    s32 temp_a0_2;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_a2;
    s32 temp_lo;
    s32 temp_lo_10;
    s32 temp_lo_11;
    s32 temp_lo_12;
    s32 temp_lo_13;
    s32 temp_lo_14;
    s32 temp_lo_15;
    s32 temp_lo_16;
    s32 temp_lo_17;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_lo_9;
    s32 temp_s0_3;
    s32 temp_s2;
    s32 temp_s2_2;
    s32 temp_s4;
    s32 temp_s4_2;
    s32 temp_s6;
    s32 temp_v0;
    s32 temp_v0_18;
    s32 temp_v0_25;
    s32 temp_v0_28;
    s32 temp_v0_2;
    s32 temp_v0_6;
    s32 temp_v1_10;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 var_fp;
    s32 var_hi;
    s32 var_s0;
    s32 var_s3_2;
    s32 var_s3_3;
    s32 var_s3_4;
    s32 var_s3_5;
    s32 var_s3_6;
    s32 var_v0_4;
    s32 var_v1;
    struct Effect *temp_v0_24;
    struct Entity *temp_a0;
    struct Entity *temp_a0_3;
    struct Entity *temp_v0_11;
    struct Entity *temp_v0_27;
    u16 temp_v0_16;
    u16 temp_v0_20;
    u16 temp_v0_3;
    u16 temp_v0_4;
    u16 temp_v0_9;
    u16 var_v0;
    u32 temp_a1;
    u32 temp_v0_15;
    u32 temp_v1_9;
    u32 var_s3;
    u32 var_v1_2;
    u8 temp_v0_19;
    u8 temp_v1;
    u8 temp_v1_12;
    u8 temp_v1_2;
    u8 temp_v1_4;
    u8 temp_v1_5;
    u8 temp_v1_8;
    u8 var_v0_2;
    void *temp_s0;
    void *temp_s0_2;
    void *temp_s0_4;

    if (*(s32 *)0x801F0074 == 0) {
        *(struct Entity **)0x801247F8 = NULL;
        *(void *)0x801F0074 = 1;
        *(u16 *)0x801247F4 = 0;
        *(s16 *)0x801247F0 = 0;
    }
    if ((e->target_anim == 0) && (e->anim_done != 0)) {
        e->cur_anim = 0xFF;
    }
    if ((e->target_anim == 1) && (e->anim_done != 0)) {
        e->cur_anim = 0xFF;
    }
    if (*(s32 *)0x801E6384 & 0x10) {
        temp_v0 = e->delay;
        var_fp = 0;
        if (temp_v0 != 0) {
            temp_v0_2 = temp_v0 - 1;
            e->delay = temp_v0_2;
            if (temp_v0_2 == 0) {
                *(s32 *)0x801F94D0 = 0;
            } else if (!(temp_v0_2 & 0x1F)) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[4] = 6;
                e->bytes[2] = (temp_lo + 0xE06A02E7) / 134217728;
            }
            temp_v0_3 = (u16) e->ai[4];
            if (temp_v0_3 != 0) {
                e->ai[4] = temp_v0_3 - 1;
                if ((g_ent->on_ground != 0) && !(g_ent->anim_flags & 0x40)) {
                    g_ent->pafx = *(&D_80023654 + (e->bytes[2] * 2)) * 0xC0;
                    g_ent->pafy = *(&D_80023694 + (e->bytes[2] * 2)) * 0xC0;
                }
            }
        }
        if (e->target_anim == 8) {
            temp_a0 = *(void *)0x801247F8;
            if (temp_a0 != NULL) {
                temp_a0->target_anim = 2;
                *(void *)0x801247F8 = NULL;
                temp_a0->flags |= 0x40;
            }
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    temp_s0 = e->unk284;
                    e->target_anim = 9;
                    temp_s0->unk88 = 1;
                    temp_s0->unk282 = 0x12C;
                    temp_s0->unk28A = 0x1E;
                    temp_s0->unk277 = (u8) e->bytes[3];
                    e->bytes[0] = 5;
                    e->bytes[1] = 0;
                    e->ai[1] = 0;
                    *(void *)0x801F94D0 = 0;
                    return;
                }
                if ((u16) e->ai[5] == 0) {
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    temp_a1 = temp_lo_2 + 0xE06A02E7;
                    g_rng_seed = temp_a1;
                    temp_lo_3 = temp_a1 * 0x7D2B89DD;
                    if (((temp_lo_2 + 0xE06A02E7) / MULHI_3) != 0) {
                        e->ai[5] = 1;
                        e->target_anim = 6;
                        g_rng_seed = temp_lo_3 + 0xE06A02E7;
                        if (((temp_lo_3 + 0xE06A02E7) / 2147483648) != 0) {
                            e->bytes[0] = 2;
                            e->bytes[1] = 2;
                        } else {
                            e->bytes[0] = 9;
                            e->bytes[1] = 2;
                        }
                    } else {
                        goto block_30;
                    }
                } else {
block_30:
                    e->target_anim = 3;
                    e->bytes[0] = 4;
                    e->bytes[1] = 0;
                    e->ai[5] = 0;
                }
                e->damaged_tick = 0x5A;
            }
        } else {
            temp_v1 = e->bytes[0];
            switch (temp_v1) {                      /* switch 1 */
            case 0:                                 /* switch 1 */
                var_v0 = (u16) e->ai[1];
                e->target_anim = 0;
                e->bytes[1] = 0;
                if (var_v0 == 0) {
                    if (e->anim_done != 0) {
                        temp_v0_4 = *(void *)0x801247F4 + 1;
                        *(void *)0x801247F4 = temp_v0_4;
                        if ((s16) temp_v0_4 < 4) {
                            temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                            g_rng_seed = temp_lo_4 + 0xE06A02E7;
                            var_s3 = (temp_lo_4 + 0xE06A02E7) / MULHI_9;
                        } else {
                            temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                            *(void *)0x801247F4 = 0U;
                            g_rng_seed = temp_lo_5 + 0xE06A02E7;
                            var_s3 = ((temp_lo_5 + 0xE06A02E7) / MULHI_3) + 4;
                        }
                        switch (var_s3) {           /* switch 2 */
                        case 3:                     /* switch 2 */
                            e->bytes[0] = 3;
                            break;
                        case 4:                     /* switch 2 */
                            if (e->delay == 0) {
                                e->bytes[0] = 7;
                                e->target_anim = 0xB;
                                e->ai[1] = 0xA;
                            } else {
block_45:
                                e->bytes[0] = 1;
                            }
                            break;
                        case 1:                     /* switch 2 */
                        case 8:                     /* switch 2 */
                            goto block_45;
                        case 5:                     /* switch 2 */
                            e->bytes[0] = 8;
                            e->ai[1] = 0x30;
                            temp_v0_5 = *(void *)0x801247F0;
                            if (temp_v0_5 == 0) {
                                temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                                temp_v0_6 = (temp_lo_6 + 0xE06A02E7) / 1073741824;
                                g_rng_seed = temp_lo_6 + 0xE06A02E7;
                                e->bytes[1] = *(&D_80028AF8 + temp_v0_6);
                                *(void *)0x801247F0 = (s16) (temp_v0_6 + 1);
                            } else {
                                e->bytes[1] = (*(&D_80028AF7 + temp_v0_5) + 0x10) & 0x1F;
                                *(void *)0x801247F0 = 0;
                            }
                            break;
                        case 2:                     /* switch 2 */
                        case 7:                     /* switch 2 */
                            e->bytes[0] = 9;
                            break;
                        case 0:                     /* switch 2 */
                        case 6:                     /* switch 2 */
block_85:
                            e->bytes[0] = 2;
                            break;
                        }
                    }
                } else {
block_137:
                    e->ai[1] = var_v0 - 1;
                }
                break;
            case 1:                                 /* switch 1 */
                temp_v1_2 = e->bytes[1];
                switch (temp_v1_2) {                /* switch 3; irregular */
                case 0:                             /* switch 3 */
                    e->ai[1] = 0x4E;
                    temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                    *(s16 *)0x801247EC = 0;
                    g_rng_seed = temp_lo_7 + 0xE06A02E7;
                    temp_v0_7 = (temp_lo_7 + 0xE06A02E7) / MULHI_3;
                    *(s16 *)0x801247E4 = temp_v0_7;
                    *(u16 *)0x801247E8 = temp_v0_7 + 2;
                    var_v1 = 4;
block_181:
                    e->target_anim = var_v1;
block_182:
                    var_v0_2 = e->bytes[1] + 1;
block_183:
                    e->bytes[1] = var_v0_2;
                    break;
                case 1:                             /* switch 3 */
                    temp_v0_8 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_8;
                    if (!(temp_v0_8 & 0xFFFF)) {
                        e->ai[1] = 1;
                        goto block_182;
                    }
                    break;
                case 2:                             /* switch 3 */
                    temp_v0_9 = (u16) e->ai[1];
                    temp_v0_10 = temp_v0_9 - 1;
                    if (temp_v0_9 != 0) {
                        e->ai[1] = temp_v0_10;
                        if (!(temp_v0_10 & 0xFFFF)) {
                            temp_v1_3 = *(void *)0x801247EC;
                            if (temp_v1_3 < 5) {
                                var_s3_2 = 0xC - (temp_v1_3 * 2);
                            } else if (temp_v1_3 < 0xA) {
                                var_s3_2 = (temp_v1_3 * 2) - 6;
                            } else {
                                var_s3_2 = 0xC - ((temp_v1_3 - 0xA) * 2);
                            }
                            temp_v0_11 = spawn_warp_entity(e, 1, 0x9F, e->px + 0xFFB80000, /* extra? */ e->py, /* extra? */ (e->pz + 0x300000), /* extra? */ var_s3_2);
                            if (temp_v0_11 != NULL) {
                                temp_v0_11->bytes[1] = 1;
                                temp_v0_11->bytes[0] = (u8) *(void *)0x801247E8;
                            }
                            temp_v0_12 = (u16) *(void *)0x801247EC + 1;
                            *(void *)0x801247EC = temp_v0_12;
                            switch (temp_v0_12) {   /* switch 4; irregular */
                            case 15:                /* switch 4 */
                            case 10:                /* switch 4 */
                                if (*(void *)0x801247E4 == 2) {
block_76:
                                    *(void *)0x801247E8 = 2U;
                                } else {
                                    *(void *)0x801247E8 = 4U;
                                }
                                break;
                            case 5:                 /* switch 4 */
                                if (*(void *)0x801247E4 != 1) {
                                    *(void *)0x801247E8 = 3U;
                                } else {
                                    goto block_76;
                                }
                                break;
                            default:                /* switch 4 */
                                e->ai[1] = 0xF;
                                break;
                            }
                        }
                    }
                    if (e->anim_done != 0) {
                        if (*(void *)0x801247EC == 0xF) {
                            e->target_anim = 0;
                            goto block_182;
                        }
                        e->target_anim = 4;
                        e->ai[1] = 0x4E;
block_118:
                        e->bytes[1] = 1;
                    }
                    break;
                case 3:                             /* switch 3 */
                    if (e->anim_done != 0) {
                        e->bytes[1] = 0;
                        temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_8 + 0xE06A02E7;
                        if (((temp_lo_8 + 0xE06A02E7) / 2147483648) == 0) {
                            goto block_85;
                        }
                        e->bytes[0] = 0;
                        temp_lo_9 = g_rng_seed * 0x7D2B89DD;
                        var_v1_2 = temp_lo_9 + 0xE06A02E7;
                        var_hi = (temp_lo_9 + 0xE06A02E7) / 268435456;
block_159:
                        g_rng_seed = var_v1_2;
                        e->ai[1] = (var_hi >> 0) + 0x1E;
                    }
                    break;
                }
                break;
            case 2:                                 /* switch 1 */
                temp_v1_4 = e->bytes[1];
                switch (temp_v1_4) {                /* switch 5 */
                case 0:                             /* switch 5 */
                    var_v1 = 2;
                    goto block_181;
                case 1:                             /* switch 5 */
                    if (e->anim_done != 0) {
                        var_v0_2 = e->bytes[1] + 1;
                        goto block_183;
                    }
                    break;
                case 2:                             /* switch 5 */
                    e->target_anim = 6;
                    e->ai[1] = 0x14;
                    goto block_182;
                case 3:                             /* switch 5 */
                    temp_v0_13 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_13;
                    var_fp = 0x40;
                    if (!(temp_v0_13 & 0xFFFF)) {
                        *(void *)0x801247F8 = spawn_warp_entity(e, 1, 0x9E, e->px + 0xFF600000, /* extra? */ (e->py + 0x300000), /* extra? */ (e->pz + 0xFFF00000), /* extra? */ e->target_dir);
                        e->item_state = 0;
                        goto block_182;
                    }
                    break;
                case 4:                             /* switch 5 */
                    temp_v0_14 = (u16) e->ai[1] + 1;
                    e->ai[1] = temp_v0_14;
                    var_fp = 0xA0;
                    if (!(temp_v0_14 & 3)) {
                        temp_lo_10 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_10 + 0xE06A02E7;
                        temp_s6 = ((temp_lo_10 + 0xE06A02E7) / 2147483648) + 2;
                        var_s3_3 = 0;
                        if (temp_s6 != 0) {
                            do {
                                temp_lo_11 = g_rng_seed * 0x7D2B89DD;
                                temp_v0_15 = temp_lo_11 + 0xE06A02E7;
                                temp_lo_12 = temp_v0_15 * 0x7D2B89DD;
                                g_rng_seed = temp_v0_15;
                                g_rng_seed = temp_lo_12 + 0xE06A02E7;
                                sp20 = temp_v0_15 * 0x19;
                                sp24 = (temp_lo_11 + 0xE06A02E7) / MULHI_25;
                                temp_a1_2 = e->item_state + 1;
                                temp_a0_2 = e->item_state * 8;
                                temp_a2 = e->item_state * 8;
                                e->item_state = temp_a1_2;
                                if (temp_a1_2 >= 6) {
                                    e->item_state = 0;
                                }
                                var_s3_3 += 1;
                                spawn_warp_entity(e, 0, 0xEC, *(&D_80027E90 + temp_a0_2) + (((temp_lo_11 + 0xE06A02E7) / MULHI_25) << 0x12), /* extra? */ (*(&D_80027E94 + temp_a2) + (((temp_lo_12 + 0xE06A02E7) / MULHI_25) << 0x11)), /* extra? */ 0x30000, /* extra? */ 0)->fz = 0x8000;
                            } while (var_s3_3 != temp_s6);
                        }
                    }
                    if (e->anim_done != 0) {
                        e->cur_anim = -1;
                        goto block_182;
                    }
                    break;
                case 5:                             /* switch 5 */
                    var_fp = 0xA0;
                    if (e->anim_done != 0) {
                        e->bytes[1] += 1;
                        temp_a0_3 = *(void *)0x801247F8;
                        e->target_anim = 1;
                        if (temp_a0_3 != NULL) {
                            temp_a0_3->target_anim = 2;
                            *(void *)0x801247F8 = NULL;
                            temp_a0_3->flags |= 0x40;
                        }
                    }
                    break;
                case 6:                             /* switch 5 */
                    if (e->anim_done != 0) {
                        if (((u16) e->ai[5] == 0) && (temp_lo_13 = g_rng_seed * 0x7D2B89DD, g_rng_seed = temp_lo_13 + 0xE06A02E7, (((temp_lo_13 + 0xE06A02E7) / 2147483648) == 0))) {
                            e->bytes[1] = 2;
                            e->ai[5] = 1;
                        } else {
                            var_v0_2 = e->bytes[1] + 1;
                            goto block_183;
                        }
                    }
                    break;
                case 7:                             /* switch 5 */
block_179:
                    var_v1 = 3;
                    if (e->anim_done != 0) {
                        goto block_181;
                    }
                    break;
                case 8:                             /* switch 5 */
                case 4:                             /* switch 8 */
                    if (e->anim_done != 0) {
                        e->bytes[0] = 0;
                        e->ai[1] = 0x1E;
                        e->ai[5] = 0;
                    }
                    break;
                }
                break;
            case 3:                                 /* switch 1 */
                temp_v1_5 = e->bytes[1];
                switch (temp_v1_5) {                /* switch 6; irregular */
                case 0:                             /* switch 6 */
                    e->target_anim = 2;
                    goto block_118;
                case 1:                             /* switch 6 */
                    if (e->anim_done != 0) {
                        e->target_anim = 3;
block_151:
                        e->bytes[1] = 2;
                    }
                    break;
                case 2:                             /* switch 6 */
                    var_v0_3 = 0x28;
                    if (e->anim_done != 0) {
                        e->bytes[0] = 0;
block_162:
                        e->ai[1] = var_v0_3;
                    }
                    break;
                }
                break;
            case 4:                                 /* switch 1 */
                var_v0_3 = 0x1E;
                if (e->anim_done != 0) {
block_161:
                    e->bytes[0] = 0;
                    goto block_162;
                }
                break;
            case 5:                                 /* switch 1 */
                temp_v1_6 = e->target_anim;
                if ((temp_v1_6 == 9) && (e->anim_done != 0)) {
                    temp_v1_7 = *(s32 *)0x801E6378;
                    var_v0_4 = temp_v1_7 & 0x20;
                    if (!(temp_v1_7 & 1)) {
                        *(s32 *)0x801E6378 = temp_v1_7 | 1;
                        var_v0_4 = *(s32 *)0x801E6378 & 0x20;
                    }
                    if (var_v0_4 != 0) {
                        temp_s0_2 = e->unk284;
                        if ((u8) temp_s0_2->unk277 < 2U) {
                            temp_s2 = temp_s0_2->unk1DC;
                            temp_s4 = temp_s0_2->unk1E0;
                            temp_a1_3 = temp_s2 + 0x500000;
                            temp_s0_2->unk1DC = temp_a1_3;
                            temp_s0_2->unk1E0 = (s32) (temp_s0_2->unk1E0 + 0x500000);
                            func_80083394(temp_s0_2, temp_a1_3);
                            temp_s0_2->unk1DC = temp_s2;
                            temp_s0_2->unk1E0 = temp_s4;
                        } else if (!(*(s32 *)0x801E6378 & 0x40)) {
                            *(s32 *)0x801E6378 |= 0x40;
                            e->target_anim = 0xA;
                            e->ai[1] = 0;
                        }
                    }
                } else if (temp_v1_6 == 0xA) {
                    temp_v0_16 = (u16) e->ai[1];
                    temp_v0_17 = temp_v0_16 - 1;
                    if (temp_v0_16 == 0) {
                        var_v0 = (u16) *(&D_80027E10 + (e->bytes[1] * 4));
                        goto block_137;
                    }
                    e->ai[1] = temp_v0_17;
                    if (!(temp_v0_17 & 0xFFFF)) {
                        temp_v0_18 = e->bytes[1] * 0xC;
                        temp_s0_3 = e->px + *(&D_80027E28 + temp_v0_18);
                        temp_s2_2 = e->py + *(&D_80027E2C + temp_v0_18) + 0x500000;
                        temp_s4_2 = e->pz + *(&D_80027E30 + temp_v0_18) + 0x500000;
                        play_sound(0xC4);
                        spawn_effect(0, 8, 0, temp_s0_3, temp_s2_2, temp_s4_2);
                        temp_v0_19 = e->bytes[1] + 1;
                        e->bytes[1] = temp_v0_19;
                        if ((temp_v0_19 & 0xFF) == 6) {
                            e->bytes[0] = 6;
                        }
                    }
                }
                break;
            case 7:                                 /* switch 1 */
                temp_v1_8 = e->bytes[1];
                switch (temp_v1_8) {                /* switch 7; irregular */
                case 0:                             /* switch 7 */
                    temp_v0_20 = (u16) e->ai[1];
                    temp_v0_21 = temp_v0_20 - 1;
                    if (temp_v0_20 != 0) {
                        e->ai[1] = temp_v0_21;
                        if (!(temp_v0_21 & 0xFFFF)) {
                            *(s32 *)0x801F94D4 = 4;
                            *(s32 *)0x801F94D8 = 2;
                            *(void *)0x801F94D0 = 1;
                            *(s32 *)0x801F94DC = 1;
                            *(s32 *)0x801F94E0 = 1;
                            e->bytes[1] = 1;
                            e->ai[1] = 0x1E;
                        }
                    }
                    break;
                case 1:                             /* switch 7 */
                    temp_v0_22 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_22;
                    if (!(temp_v0_22 & 0xFFFF)) {
                        goto block_151;
                    }
                    break;
                case 2:                             /* switch 7 */
                    temp_v0_23 = (u16) e->ai[1] + 1;
                    e->ai[1] = temp_v0_23;
                    if (!(temp_v0_23 & 0xF)) {
                        var_s3_4 = 0;
                        var_s0 = 0;
                        do {
                            temp_lo_14 = g_rng_seed * 0x7D2B89DD;
                            temp_v1_9 = temp_lo_14 + 0xE06A02E7;
                            temp_lo_15 = temp_v1_9 * 0x7D2B89DD;
                            g_rng_seed = temp_v1_9;
                            g_rng_seed = temp_lo_15 + 0xE06A02E7;
                            sp20 = temp_v1_9 * 0xF;
                            sp24 = (temp_lo_14 + 0xE06A02E7) / MULHI_15;
                            temp_v0_24 = spawn_effect(0, 0x16, 1, *(&D_80027E70 + var_s0) + (((temp_lo_14 + 0xE06A02E7) / MULHI_15) * 0xC0000), *(&D_80027E74 + var_s0) + (((temp_lo_15 + 0xE06A02E7) / MULHI_19) << 0x13), 0x01100000);
                            if (temp_v0_24 != NULL) {
                                temp_lo_16 = g_rng_seed * 0x7D2B89DD;
                                g_rng_seed = temp_lo_16 + 0xE06A02E7;
                                temp_v0_24->vz = (((temp_lo_16 + 0xE06A02E7) / MULHI_5) << 0xE) + 0xFFFC0000;
                            }
                            var_s3_4 += 1;
                            var_s0 += 8;
                        } while (var_s3_4 != 4);
                    }
                    if (e->anim_done != 0) {
                        *(void *)0x801F94D4 = 2;
                        e->bytes[0] = 0;
                        temp_lo_17 = g_rng_seed * 0x7D2B89DD;
                        var_v1_2 = temp_lo_17 + 0xE06A02E7;
                        var_hi = (temp_lo_17 + 0xE06A02E7) / 268435456;
                        e->delay = 0x258;
                        goto block_159;
                    }
                    break;
                }
                break;
            case 8:                                 /* switch 1 */
                temp_s0_4 = e->unk284;
                temp_v1_10 = *(&D_80023654 + (e->bytes[1] * 2)) * 0x30;
                temp_s0_4->unkCC = temp_v1_10;
                e->pafx = temp_v1_10;
                temp_v0_25 = *(&D_80023694 + (e->bytes[1] * 2)) * 0x30;
                temp_s0_4->unkD0 = temp_v0_25;
                e->pafy = temp_v0_25;
                temp_v1_11 = (u16) e->ai[1] - 1;
                e->ai[1] = temp_v1_11;
                var_v0_3 = 0x1E;
                if (!(temp_v1_11 & 0xFFFF)) {
                    goto block_161;
                }
                break;
            case 9:                                 /* switch 1 */
                temp_v1_12 = e->bytes[1];
                switch (temp_v1_12) {               /* switch 8 */
                case 0:                             /* switch 8 */
                    var_v1 = 2;
                    goto block_181;
                case 1:                             /* switch 8 */
                    if (e->anim_done != 0) {
                        var_v0_2 = e->bytes[1] + 1;
                        goto block_183;
                    }
                    break;
                case 2:                             /* switch 8 */
                    e->target_anim = 6;
                    e->ai[1] = 0x14;
                    e->bytes[1] += 1;
                    *(void *)0x801247EC = 0;
                    if (g_ent->py <= 0x012FFFFF) {
                        *(void *)0x801247E4 = 0;
                    } else {
                        *(void *)0x801247E4 = 1;
                    }
                    break;
                case 3:                             /* switch 8 */
                    temp_a1_4 = *(void *)0x801247EC;
                    if (temp_a1_4 != 6) {
                        temp_v0_26 = (u16) e->ai[1] - 1;
                        e->ai[1] = temp_v0_26;
                        if (!(temp_v0_26 & 0xFFFF)) {
                            if (*(void *)0x801247E4 == 0) {
                                var_s3_5 = 0xF - (temp_a1_4 * 2);
                            } else {
                                var_s3_5 = (temp_a1_4 * 2) + 1;
                            }
                            temp_v0_27 = spawn_warp_entity(e, 1, 0x9F, e->px + 0xFF880000, /* extra? */ (e->py + 0x100000), /* extra? */ e->pz, /* extra? */ var_s3_5);
                            if (temp_v0_27 != NULL) {
                                temp_v0_27->bytes[0] = 4;
                                temp_v0_27->bytes[1] = 9;
                            }
                            e->ai[1] = 0xA;
                            *(void *)0x801247EC = (s16) ((u16) *(void *)0x801247EC + 1);
                        }
                    }
                    goto block_179;
                }
                break;
            }
            var_s3_6 = 0;
            if (var_fp != 0) {
                var_v1_3 = &g_ent->pafx;
                temp_a0_4 = var_v1_3;
                do {
                    if ((var_v1_3 == temp_a0_4) || (temp_v0_28 = var_v1_3->unk-64, (temp_v0_28 == 2)) || ((temp_v0_28 == 0xEC) && (var_v1_3->unk-44 == 0))) {
                        var_v1_3->unk0 = D_80023664 * var_fp;
                    }
                    var_s3_6 += 1;
                    var_v1_3 += 0x294;
                } while (var_s3_6 != 0x40);
            }
        }
    }
}
