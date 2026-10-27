/* 8007C32C: built-in program C55 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
? func_8007C2EC(struct Effect *);                   /* extern */
? func_800832B0();                                  /* extern */
extern ? D_80023654;
extern ? D_80023694;
extern ? D_800280B0;
extern ? D_800280C8;
extern ? D_80028AF8;

void AI_C55(struct Entity *e) {
    ? *var_s1;
    ? *var_s5;
    s16 temp_s4;
    s16 temp_v0_10;
    s16 temp_v0_7;
    s16 var_s1_2;
    s16 var_s4;
    s16 var_v0;
    s32 temp_a0;
    s32 temp_a2;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_s2;
    s32 temp_s2_2;
    s32 temp_s3;
    s32 temp_t2;
    s32 temp_v0;
    s32 temp_v1_3;
    s32 var_lo;
    s32 var_s1_3;
    s32 var_s2;
    s32 var_s3;
    s32 var_s3_2;
    s32 var_s3_3;
    struct Effect *temp_a0_2;
    struct Effect *temp_v1_6;
    struct Entity *temp_v0_5;
    struct Entity *temp_v0_8;
    struct Entity *temp_v0_9;
    u16 temp_v0_2;
    u16 temp_v0_6;
    u16 temp_v1_5;
    u32 temp_v1_2;
    u8 temp_s1;
    u8 temp_v0_3;
    u8 temp_v0_4;
    u8 temp_v1;
    void *temp_v1_4;

    if (*(s32 *)0x801F0074 == 0) {
        *(struct Effect **)0x80124850 = NULL;
        *(s32 *)0x8012484C = 0;
        *(void *)0x801F0074 = 1;
    }
    func_8007C2EC(*(void *)0x80124850);
    func_8007C2EC(e->unk284);
    temp_v0 = e->target_anim;
    switch (temp_v0) {                              /* switch 1 */
    case 14:                                        /* switch 1 */
        temp_v0_2 = (u16) e->ai[1];
        var_v0 = temp_v0_2 - 1;
        if (temp_v0_2 == 0) {
            if ((u16) e->ai[4] == 0) {
                temp_v1 = e->bytes[0];
                switch (temp_v1) {                  /* switch 2; irregular */
                case 1:                             /* switch 2 */
                    play_sound(0x12A);
                    e->unk284 = spawn_effect(1, 0, 0, e->px, e->py, e->pz);
                    e->bytes[0] += 1;
                    return;
                case 2:                             /* switch 2 */
                    temp_v0_3 = e->unk284->b70;
                    if (temp_v0_3 == 1) {
                        e->target_anim = (s32) temp_v0_3;
                    }
                    if (e->bytes[0] == 0) {
                    case 0:                         /* switch 2 */
                        temp_lo = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo + 0xE06A02E7;
                        temp_v0_4 = (temp_lo + 0xE06A02E7) / MULHI_3;
                        e->bytes[1] = temp_v0_4;
                        if (!(temp_v0_4 & 0xFF)) {
                            var_s5 = &D_800280B0;
                            *(void *)0x8012484C = 2;
                        } else {
                            if (e->bytes[2] != 0) {
                                e->bytes[1] = 2;
                            }
                            var_s5 = &D_800280C8;
                            *(void *)0x8012484C = 3;
                        }
                        temp_a0 = *(void *)0x8012484C;
                        temp_v1_2 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                        var_s3 = 0;
                        g_rng_seed = temp_v1_2;
                        temp_a2 = (s32) MULTU_HI(temp_v1_2, (temp_a0 + 1)) >> 0;
                        var_s2 = temp_a2 * 2;
                        if (temp_a0 != 0) {
                            var_s4 = 0;
                            var_s1 = (temp_a2 * 8) + var_s5;
                            do {
                                temp_v0_5 = spawn_warp_entity(e, 1, 0xA8, var_s1->unk0, /* extra? */ var_s1->unk4, /* extra? */ e->pz, /* extra? */ e->target_dir);
                                if (temp_v0_5 != NULL) {
                                    temp_v0_5->target_anim = 0xE;
                                    temp_v0_5->bytes[0] = 1;
                                    temp_v0_5->ai[1] = var_s4;
                                }
                                temp_v1_3 = *(void *)0x8012484C;
                                var_s2 += 2;
                                var_s1 += 8;
                                if (((temp_v1_3 + 1) * 2) == var_s2) {
                                    var_s1 = var_s5;
                                    var_s2 = 0;
                                }
                                var_s3 += 1;
                                var_s4 += 0xB;
                            } while (var_s3 != temp_v1_3);
                        }
                        temp_v1_4 = (var_s2 * 4) + var_s5;
                        e->bytes[0] = 1;
                        e->ai[1] = var_s3 * 0xB;
                        e->px = temp_v1_4->unk0;
                        e->py = temp_v1_4->unk4;
                        return;
                    }
                    break;
                }
            } else {
            default:                                /* switch 1 */
                return;
            }
        } else {
block_57:
            e->ai[1] = var_v0;
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[1] == 0) {
                e->target_anim = 4;
                return;
            }
            play_sound(0x128);
            e->target_anim = 3;
            e->ai[1] = 0x1E;
            e->bytes[0] = 0;
            return;
        }
        break;
    case 3:                                         /* switch 1 */
        temp_v0_6 = (u16) e->ai[1];
        temp_v0_7 = temp_v0_6 - 1;
        if (temp_v0_6 != 0) {
            e->ai[1] = temp_v0_7;
            if (!(temp_v0_7 & 0xFFFF)) {
                if (e->bytes[0] == 0) {
                    play_sound(0x12A);
                    *(void *)0x80124850 = spawn_effect(1, 0, 0, 0x01500000, 0x03100000, 0x01400000);
                    e->bytes[0] = 1;
                    return;
                }
block_69:
                e->target_anim = 2;
                return;
            }
        } else {
            temp_s1 = (*(void *)0x80124850)->b70;
            if (temp_s1 == 1) {
                func_800832B0();
                if (e->bytes[1] == temp_s1) {
                    play_sound(0x129);
                    e->target_anim = 2;
                    var_s3_2 = 4;
                    do {
                        temp_v0_8 = spawn_warp_entity(e, 1, 0xA7, 0x01500000, /* extra? */ 0x03100000, /* extra? */ 0x01480000, /* extra? */ var_s3_2);
                        if (temp_v0_8 != NULL) {
                            temp_v0_8->bytes[0] = 4;
                            temp_v0_8->ai[1] = 0x78;
                            temp_v0_8->target_anim = 1;
                            e->bytes[2] = 3;
                        }
                        var_s3_2 += 0xC;
                    } while (var_s3_2 != 0x28);
                    return;
                }
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                var_s3_3 = 0;
                e->target_anim = 2;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                temp_s2 = ((temp_lo_2 + 0xE06A02E7) / MULHI_3) + 1;
                var_s1_2 = temp_s2 * 0x10;
                play_sound(0x127);
                do {
                    temp_v0_9 = spawn_warp_entity(e, 1, 0xA4, 0x01500000, /* extra? */ 0x03100000, /* extra? */ 0x01480000, /* extra? */ 0);
                    if (temp_v0_9 != NULL) {
                        temp_v0_9->target_anim = 0;
                        temp_v0_9->item_state = temp_s2 << 9;
                        temp_v0_9->ai[4] = var_s1_2;
                        var_s1_2 = (var_s1_2 + 0x40) & 0x1FF;
                        e->ai[4] = (u16) e->ai[4] + 1;
                    }
                    var_s3_3 += 1;
                } while (var_s3_3 != 8);
                return;
            }
        }
        break;
    case 4:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 5;
            e->ai[1] = 0xB4;
            return;
        }
        break;
    case 5:                                         /* switch 1 */
        temp_v1_5 = (u16) e->ai[1];
        switch (temp_v1_5) {                        /* switch 3; irregular */
        case 0x0:                                   /* switch 3 */
            e->target_anim = 6;
            return;
        case 0xB4:                                  /* switch 3 */
        case 0x78:                                  /* switch 3 */
        case 0x3C:                                  /* switch 3 */
            play_sound(0x125);
            var_s1_3 = 0;
            func_800832B0();
            temp_s2_2 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py) * 2;
            temp_s4 = *(&D_80023654 + temp_s2_2);
            temp_s3 = e->pz + 0x80000;
            var_lo = temp_s4 * 0;
loop_53:
            temp_a3 = e->px + var_lo;
            temp_t2 = e->py + (*(&D_80023694 + temp_s2_2) * var_s1_3);
            if (((u32) (temp_a3 + 0xFF6FFFFF) <= 0x017FFFFEU) && ((u32) (temp_t2 + 0xFD8FFFFF) <= 0x013FFFFEU)) {
                temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                var_s1_3 += 0xC00;
                g_rng_seed = temp_lo_3 + 0xE06A02E7;
                spawn_warp_entity(e, 1, 0xA3, temp_a3, /* extra? */ temp_t2, /* extra? */ temp_s3, /* extra? */ (s32) *(((temp_lo_3 + 0xE06A02E7) / 1073741824) + &D_80028AF8));
                var_lo = temp_s4 * var_s1_3;
                goto loop_53;
            }
            /* fallthrough */
        default:                                    /* switch 3 */
            var_v0 = (u16) e->ai[1] - 1;
            goto block_57;
        }
        break;
    case 6:                                         /* switch 1 */
        if (e->anim_done != 0) {
            goto block_69;
        }
        break;
    case 2:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->bytes[0] = 0;
            e->ai[1] = 0xB4;
            temp_v1_6 = *(void *)0x80124850;
            e->target_anim = 0xE;
            if (temp_v1_6 != NULL) {
                temp_v1_6->b70 = 2;
                *(void *)0x80124850 = NULL;
            }
            e->unk284->b70 = 2;
            e->unk284 = NULL;
            return;
        }
        break;
    case 7:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 0xF;
                e->ai[1] = 0x3C;
                temp_a0_2 = *(void *)0x80124850;
                e->flags &= ~3;
                if (temp_a0_2 != NULL) {
                    temp_a0_2->b70 = 2;
                    *(void *)0x80124850 = NULL;
                    return;
                }
            } else {
                goto block_69;
            }
        }
        break;
    case 15:                                        /* switch 1 */
        temp_v0_10 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_10;
        if (!(temp_v0_10 & 0xFFFF)) {
            *(s32 *)0x801E6378 |= 1;
            g_ent->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
        }
        break;
    }
}
