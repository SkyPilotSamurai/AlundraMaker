/* 800762E8: built-in program C47 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_80075DA4(struct Entity *, s32, s32, s32);    /* extern */
? func_80075F18(struct Entity *);                   /* extern */
? func_800761C0(struct Entity *, s32, s32);         /* extern */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_800282D8;
extern ? D_800286D8;

void AI_C47(struct Entity *e) {
    s32 sp20;
    s16 *var_a3_2;
    s16 *var_t0;
    s16 *var_v1_8;
    s16 temp_v0_8;
    s32 *var_a0;
    s32 *var_a3;
    s32 *var_s3;
    s32 temp_a0;
    s32 temp_a0_3;
    s32 temp_a0_5;
    s32 temp_a1_2;
    s32 temp_a2;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_t0;
    s32 temp_t0_2;
    s32 temp_t1;
    s32 temp_t3;
    s32 temp_v0_10;
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v0_4;
    s32 temp_v0_5;
    s32 temp_v0_6;
    s32 temp_v0_7;
    s32 temp_v0_9;
    s32 temp_v1;
    s32 temp_v1_10;
    s32 temp_v1_11;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_5;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 temp_v1_9;
    s32 var_a0_2;
    s32 var_a0_3;
    s32 var_a0_4;
    s32 var_a1;
    s32 var_a2;
    s32 var_a2_2;
    s32 var_a2_3;
    s32 var_s1;
    s32 var_s1_2;
    s32 var_s1_3;
    s32 var_s1_4;
    s32 var_s4;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v1;
    s32 var_v1_2;
    s32 var_v1_4;
    s32 var_v1_6;
    s32 var_v1_7;
    struct Entity *var_v1_3;
    u16 temp_v0;
    u32 temp_a0_2;
    u32 temp_a1;
    u8 temp_a0_4;
    u8 temp_a0_6;
    u8 temp_v1_12;
    u8 temp_v1_13;
    u8 temp_v1_14;
    u8 temp_v1_4;
    u8 temp_v1_8;
    u8 var_v0_4;
    void *var_a1_2;
    void *var_s2;
    void *var_v1_5;

    if (*(s32 *)0x801F0074 == 0) {
        *(s32 *)0x8012479C = 0;
        *(s32 *)0x80124798 = 0;
        *(s32 *)0x80124794 = 0;
        *(s32 *)0x80124790 = 0;
        *(s32 *)0x8012478C = 0;
        *(s32 *)0x80124788 = 0;
        *(void *)0x801F0074 = 1;
    }
    rel_tile(e, &sp20);
    if ((e->ffx != 0) || (e->ffy != 0)) {
        temp_v1 = *(void *)0x80124788;
        temp_a0 = temp_v1 * 2;
        (temp_a0 + 0x80150000)->unk34C0 = (s16) e->target_dir;
        (temp_a0 + 0x801B0000)->unk6C60 = (s16) e->unk116;
        *(void *)0x80124788 = (s32) ((temp_v1 + 1) & 0xFF);
        (temp_a0 + 0x801B0000)->unk6E60 = (s16) e->unk11A;
    }
    var_a2 = (*(void *)0x80124788 - 0x54) & 0xFF;
    if (*(void *)0x8012479C == 0) {
        var_s1 = 0;
        var_a0 = &g_ent[0x10].py;
        do {
            var_v0 = var_a2 + 6;
            if (var_a0->unk-108 == 2) {
                temp_v1_2 = var_a2 * 2;
                var_a0->unk-8C = (s32) *(0x801534C0 + temp_v1_2);
                var_a0->unk-4 = (s32) (*(0x801B6C60 + temp_v1_2) << 0x10);
                var_a0->unk0 = *(0x801B6E60 + temp_v1_2) << 0x10;
                var_v0 = var_a2 + 6;
            }
            var_a2 = var_v0 & 0xFF;
            var_s1 += 1;
            var_a0 -= 0x294;
        } while (var_s1 != 0xE);
    }
    temp_v1_3 = e->target_anim;
    switch (temp_v1_3) {                            /* switch 1 */
    case 0:                                         /* switch 1 */
    case 1:                                         /* switch 1 */
        e->target_anim = 0;
        if (e->bytes[3] == 0) {
            temp_v0 = (u16) e->ai[1];
            if (temp_v0 != 0) {
                e->ai[1] = temp_v0 - 1;
            } else if (e->bytes[0] == 0) {
                if (*(s32 *)0x801E6378 & 1) {
                    temp_v0_2 = e->target_dir;
                    *(void *)0x80124798 = temp_v0_2;
                    var_v1 = 0xFF900000;
                    if (temp_v0_2 == 0) {
                        var_v1 = 0x700000;
                    }
                    *(void *)0x80124794 = (s32) (e->py + var_v1);
                    e->target_anim = 2;
                    *(void *)0x80124790 = (s32) e->px;
                    e->bytes[0] = 1;
                    e->ai[1] = 6;
                }
            } else {
                temp_v1_4 = e->bytes[1];
                switch (temp_v1_4) {                /* switch 2 */
                case 0:                             /* switch 2 */
                case 1:                             /* switch 2 */
                case 2:                             /* switch 2 */
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    e->target_anim = 2;
                    g_rng_seed = temp_lo + 0xE06A02E7;
                    e->target_dir = (e->target_dir + ((temp_lo + 0xE06A02E7) / MULHI_9) + 8) & 0x1F;
                    break;
                case 3:                             /* switch 2 */
                    e->target_anim = 2;
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    e->target_dir = dir_from_delta(*(void *)0x80124790 - e->px, *(void *)0x80124794 - e->py);
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    temp_a0_2 = (temp_lo_2 + 0xE06A02E7) / MULHI_5;
                    switch (temp_a0_2) {            /* switch 3 */
                    case 0:                         /* switch 3 */
                    case 3:                         /* switch 3 */
                        e->bytes[2] = 1;
                        break;
                    case 2:                         /* switch 3 */
                        e->bytes[2] = 0;
                        break;
                    case 1:                         /* switch 3 */
                    case 4:                         /* switch 3 */
                        e->bytes[2] = 3;
                        break;
                    }
                    break;
                case 4:                             /* switch 2 */
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    temp_a1 = temp_lo_3 + 0xE06A02E7;
                    e->target_anim = 2;
                    g_rng_seed = temp_a1;
                    temp_lo_4 = temp_a1 * 0x7D2B89DD;
                    if (((temp_lo_3 + 0xE06A02E7) / 1073741824) == 0) {
                        var_a0_2 = g_ent->px - e->px;
                        var_a1 = g_ent->py - e->py;
block_90:
                        e->target_dir = dir_from_delta(var_a0_2, var_a1);
                    } else {
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        e->target_dir = (e->target_dir + (((temp_lo_4 + 0xE06A02E7) / MULHI_9) - 4)) & 0x1F;
                    }
                    break;
                case 5:                             /* switch 2 */
                    var_s1_2 = 0;
                    if (e->bytes[2] == 0) {
                        var_a2_2 = 0;
                        var_a3 = &e->py;
                        var_a1_2 = e + 0x3AC;
                        do {
                            temp_v1_5 = var_a3->unk160;
                            temp_v0_3 = var_a1_2->unk160;
                            temp_v1_6 = temp_v1_5 - temp_v0_3;
                            if (temp_v1_5 == temp_v0_3) {
                                var_a2_2 += 1;
                            } else {
                                if (((u32) (temp_v1_6 - 1) < 0xFFU) || (var_v1_2 = -4, ((temp_v1_6 < -0x100) != 0))) {
                                    var_v1_2 = 4;
                                }
                                var_a0_3 = (var_a1_2->unk160 + var_v1_2) & 0x1FF;
                                var_a1_2->unk160 = var_a0_3;
                                if (var_a0_3 < 0) {
                                    var_a0_3 += 0xF;
                                }
                                var_a1_2->unk-8C = (s32) (var_a0_3 >> 4);
                                var_a1_2->unk-4 = (s32) (var_a3->unk-4 + (*((var_a1_2->unk160 * 2) + &D_800282D8) * 0x500));
                                var_a1_2->unk0 = (s32) (var_a3->unk0 - (*((var_a1_2->unk160 * 2) + &D_800286D8) * 0x500));
                            }
                            var_s1_2 += 1;
                            var_a1_2 += 0x294;
                            var_a3 += 0x294;
                        } while (var_s1_2 != 0xE);
                        if (var_a2_2 != var_s1_2) {

                        } else {
                            goto block_59;
                        }
                    } else {
                        var_s3 = &e->py;
                        var_s2 = e + 0x3AC;
                        var_s4 = 0x500;
                        do {
                            temp_a0_3 = *(void *)0x8012478C;
                            var_s2->unk-8C = dir_from_delta(var_s3->unk-4 - var_s2->unk-4, var_s3->unk0 - var_s2->unk0);
                            temp_v1_7 = ((e->delay + (temp_a0_3 * ((var_s1_2 / 2) + 1))) & 0x1FF) * 2;
                            temp_t0 = *(temp_v1_7 + &D_800282D8) * var_s4;
                            temp_lo_5 = *(&D_800286D8 + temp_v1_7) * var_s4;
                            var_s1_2 += 1;
                            var_s4 += 4;
                            var_s2->unk-4 = (s32) (var_s3->unk-4 + temp_t0);
                            temp_v0_4 = var_s3->unk0;
                            var_s3 += 0x294;
                            var_s2->unk0 = (s32) (temp_v0_4 - temp_lo_5);
                            var_s2 += 0x294;
                        } while (var_s1_2 != 0xE);
                        temp_v1_8 = e->bytes[2];
                        if (temp_v1_8 != 2) {
                            if ((s32) temp_v1_8 < 3) {
                                temp_v1_9 = temp_a0_3 + 1;
                                if (temp_v1_8 != 1) {

                                } else {
                                    *(void *)0x8012478C = temp_v1_9;
                                    if (temp_v1_9 == 0x20) {
                                        e->bytes[2] += 1;
                                        play_sound(0x10A);
                                    }
                                }
                            } else if (temp_v1_8 != 3) {
                                temp_v0_5 = temp_a0_3 - 1;
                                if (temp_v1_8 != 4) {

                                } else {
                                    *(void *)0x8012478C = temp_v0_5;
                                    var_a2_3 = 0x54;
                                    if (temp_v0_5 == 0) {
                                        var_t0 = (s16 *)0x801B6D08;
                                        var_a0_4 = 0;
                                        var_a3_2 = (s16 *)0x801534C0;
                                        e->bytes[1] = 4;
                                        e->ai[1] = 0x28;
                                        *(void *)0x8012479C = 0;
                                        temp_v0_6 = e->target_dir << 5;
                                        do {
                                            temp_t3 = *(&D_800282D8 + temp_v0_6) * var_a0_4;
                                            temp_v1_10 = var_a2_3 * 2;
                                            temp_lo_6 = *(temp_v0_6 + &D_800286D8) * var_a0_4;
                                            var_a2_3 -= 1;
                                            *var_a3_2 = (s16) e->target_dir;
                                            var_a3_2 += 2;
                                            var_a0_4 += 0xD5;
                                            *var_t0 = (s16) ((s32) (e->px + temp_t3) >> 0x10);
                                            (temp_v1_10 + 0x801B0000)->unk6E60 = (s16) ((s32) (e->py - temp_lo_6) >> 0x10);
                                            var_t0 -= 2;
                                        } while (var_a2_3 >= 0);
                                        *(void *)0x80124788 = 0x55;
                                        var_v1_3 = e;
                                        if (e != &g_ent[0x11]) {
loop_65:
                                            var_v1_3->target_dir = e->target_dir;
                                            var_v1_3 += 0x294;
                                            if (var_v1_3 != &g_ent[0x11]) {
                                                goto loop_65;
                                            }
                                        }
                                    }
                                }
                            } else {
                                var_v1_4 = temp_a0_3 + 4;
                                *(void *)0x8012478C = var_v1_4;
                                var_v0_2 = 0x14;
                                goto block_58;
                            }
                        } else {
                            var_v1_4 = temp_a0_3 - 4;
                            *(void *)0x8012478C = var_v1_4;
                            var_v0_2 = -0x20;
block_58:
                            if (var_v1_4 == var_v0_2) {
block_59:
                                e->bytes[2] += 1;
                            }
                        }
                    }
                    break;
                case 7:                             /* switch 2 */
                    var_s1_3 = 0;
                    var_v1_5 = e + 0x2A8;
                    do {
                        temp_v0_7 = var_v1_5->unk54;
                        if ((temp_v0_7 == 0x1E9) || (temp_v0_7 == 0x1EC)) {
                            var_v0_3 = var_v1_5->unk4;
                            var_v1_5->unk74 = 0xE;
                            var_v1_5->unk263 = 0;
                            if (var_v0_3 < 0) {
                                var_v0_3 += 3;
                            }
                            var_v1_5->unk0 = (s32) (var_v0_3 >> 2);
                        }
                        var_s1_3 += 1;
                        var_v1_5 += 0x294;
                    } while (var_s1_3 != 0xE);
                    e->bytes[1] = 8;
                    e->ai[1] = 0x40;
                    break;
                case 8:                             /* switch 2 */
                    e->bytes[1] = 4;
                    e->ai[1] = 0x28;
                    break;
                }
            }
        }
        break;
    case 2:                                         /* switch 1 */
    case 3:                                         /* switch 1 */
        e->target_anim = 2;
        if (e->bytes[0] != 0xF) {
            func_800761C0(e, *(void *)0x80124794, *(void *)0x80124798);
        } else {
            temp_a0_4 = e->bytes[1];
            temp_v1_11 = temp_a0_4 & 0xFF;
            if (temp_v1_11 == 6) {
                temp_v0_8 = (u16) e->ai[1] - 1;
                e->ai[1] = temp_v0_8;
                if (!(temp_v0_8 & 0xFFFF)) {
                    e->target_dir = (e->target_dir + e->item_state) & 0x1F;
                    e->ai[1] = 4;
                    if (e->target_dir == e->delay) {
                        e->ai[1] = 0x3C;
                        var_v0_4 = 7;
                        e->target_anim = 0;
                        goto block_112;
                    }
                }
            } else if (temp_v1_11 == 3) {
                temp_t1 = e->px;
                temp_a0_5 = *(void *)0x80124790;
                temp_t0_2 = e->py;
                temp_a1_2 = *(void *)0x80124794;
                temp_a3 = temp_t1 - temp_a0_5;
                var_v1_6 = temp_a3;
                if (temp_a3 < 0) {
                    var_v1_6 = -var_v1_6;
                }
                temp_a2 = temp_t0_2 - temp_a1_2;
                if (var_v1_6 <= 0x180000) {
                    var_v1_7 = temp_a2;
                    if (temp_a2 < 0) {
                        var_v1_7 = -var_v1_7;
                    }
                    if (var_v1_7 > 0x100000) {
                        goto block_89;
                    }
                    temp_v1_12 = e->bytes[2];
                    e->target_anim = 0;
                    e->sfy = 0;
                    e->sfx = 0;
                    e->fy = 0;
                    e->fx = 0;
                    e->tfy = 0;
                    e->tfx = 0;
                    if (temp_v1_12 == 1) {
                        *(void *)0x8012478C = 0;
                        *(void *)0x8012479C = (s32) temp_v1_12;
                    }
                    func_80075DA4(e, temp_a1_2, temp_a2, temp_a3);
                } else {
block_89:
                    var_a0_2 = temp_a0_5 - temp_t1;
                    var_a1 = temp_a1_2 - temp_t0_2;
                    goto block_90;
                }
            } else if (e->force_adjusted != 0) {
                if ((u32) (temp_a0_4 - 1) < 2U) {
                    temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_7 + 0xE06A02E7;
                    if ((((temp_lo_7 + 0xE06A02E7) / MULHI_3) == 0) && ((u16) e->ai[4] < 5U)) {
                        spawn_warp_entity(e, 1, 0xF9, g_ent[0x10].px, /* extra? */ g_ent[0x10].py, /* extra? */ e->pz, /* extra? */ 0);
                    }
                }
                temp_a0_6 = e->bytes[1];
                e->ai[1] = 0x3C;
                e->target_anim = 0;
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                if ((temp_a0_6 & 0xFF) != 4) {
                    var_v0_4 = temp_a0_6 + 1;
                } else {
                    var_v0_4 = 1;
                }
block_112:
                e->bytes[1] = var_v0_4;
            }
        }
        break;
    case 6:                                         /* switch 1 */
    case 7:                                         /* switch 1 */
        if (e->anim_done != 0) {
            var_s1_4 = 0;
            if (e->bytes[3] != 0) {
                var_v1_8 = &e->ai[5];
                e->target_anim = 0;
                *(void *)0x8012479C = 1;
                do {
                    var_s1_4 += 1;
                    var_v1_8->unk-8 = 0x12C;
                    var_v1_8->unk0 = 0x1E;
                    var_v1_8->unk-21E = (s32) (var_v1_8->unk-21E & ~3);
                    var_v1_8 += 0x294;
                } while (var_s1_4 != 0xF);
            } else {
                temp_v1_13 = e->bytes[1];
                e->damaged_tick = 0x5A;
                e->target_anim = 2;
                if ((temp_v1_13 != 6) && ((temp_v1_13 != 3) || (e->bytes[2] != 2))) {
                    temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_8 + 0xE06A02E7;
                    var_v0_4 = 1;
                    if (((temp_lo_8 + 0xE06A02E7) / MULHI_3) == 0) {
                        e->bytes[1] = 3;
                        e->bytes[2] = 2;
                    } else {
                        goto block_112;
                    }
                }
            }
        }
        break;
    }
    func_80075F18(e);
    temp_v1_14 = e->bytes[3];
    if ((temp_v1_14 != 0) && ((u32) e->target_anim < 2U)) {
        if (temp_v1_14 < 4U) {
            func_80083394(e);
            func_80083394(e + 0x14A0);
            return;
        }
        temp_v0_9 = e->delay + 1;
        e->delay = temp_v0_9;
        if (temp_v0_9 == 0xA) {
            e->delay = 0;
            *(&g_ent->target_anim + (e->bytes[1] * 0x294)) = 8;
            temp_v0_10 = e->bytes[1] * 0x294;
            *(&g_ent->flags + temp_v0_10) = *(&g_ent->flags + temp_v0_10) | 0x40;
            e->bytes[1] -= 1;
        }
    }
}
