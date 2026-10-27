/* 80064E14: built-in program C90 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80023654;
extern ? D_80026CEC;
extern s32 D_80026CF4;
extern ? D_800282D8;
extern ? D_800286D8;

void AI_C90(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s16 temp_v0_10;
    s16 temp_v0_11;
    s16 temp_v0_17;
    s16 temp_v0_18;
    s16 temp_v0_20;
    s16 temp_v0_22;
    s16 temp_v0_4;
    s16 temp_v0_6;
    s16 temp_v0_7;
    s16 temp_v0_9;
    s16 temp_v1_10;
    s16 temp_v1_5;
    s16 var_a3;
    s16 var_v0_3;
    s16 var_v0_7;
    s32 *var_a0;
    s32 *var_s2;
    s32 temp_a0;
    s32 temp_s4;
    s32 temp_s5;
    s32 temp_s6;
    s32 temp_t0;
    s32 temp_v0;
    s32 temp_v0_12;
    s32 temp_v0_14;
    s32 temp_v0_23;
    s32 temp_v0_3;
    s32 temp_v0_5;
    s32 temp_v0_8;
    s32 temp_v1;
    s32 temp_v1_11;
    s32 temp_v1_12;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 temp_v1_8;
    s32 temp_v1_9;
    s32 var_a1;
    s32 var_a1_2;
    s32 var_a1_3;
    s32 var_a1_4;
    s32 var_a1_5;
    s32 var_fp;
    s32 var_v0;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v0_8;
    s32 var_v0_9;
    struct Entity *temp_s0;
    struct Entity *temp_s0_2;
    struct Entity *temp_s3;
    struct Entity *var_s0;
    struct Entity *var_s0_2;
    struct Entity *var_s0_3;
    u16 temp_v0_13;
    u16 temp_v0_15;
    u16 temp_v0_16;
    u16 temp_v0_19;
    u16 temp_v0_21;
    u16 temp_v0_2;
    u32 var_v0_2;
    u8 temp_a0_2;
    u8 temp_a1;
    u8 temp_s7;
    u8 temp_v1_13;
    u8 temp_v1_2;
    void *temp_s2;
    void *var_v1;

    if (*(s32 *)0x801F0074 == 0) {
        var_s2 = (s32 *)0x801246E4;
        var_a1 = 0;
        var_v1 = (void *)0x80124700;
        var_a0 = &D_80026CF4;
        do {
            temp_v0 = *var_a0;
            var_a0 += 4;
            var_a1 += 1;
            *var_s2 = 0x600;
            var_s2 += 0x20;
            var_v1->unk-18 = 0;
            var_v1->unk-14 = 0x2200;
            var_v1->unk-10 = 0;
            var_v1->unk-E = 0;
            var_v1->unk-C = 0;
            var_v1->unk-4 = 0x200000;
            var_v1->unk0 = 0;
            var_v1->unk-8 = temp_v0;
            var_v1 += 0x20;
        } while (var_a1 != 2);
        *(void *)0x801F0074 = 1;
    }
    if ((u32) (e->target_anim - 7) >= 2U) {
        var_s0 = e;
        var_a1_2 = 0;
        temp_s7 = e->bytes[0];
        temp_v1 = temp_s7 << 5;
        temp_s2 = temp_v1 + 0x801246E4;
        temp_t0 = *(&D_80026CEC + (temp_s7 * 4));
        var_a3 = temp_s2->unkC;
        do {
            temp_a0 = ((7 - var_a1_2) << 7) / 7;
            var_s0->px = temp_t0 + ((s32) ((temp_s2->unk14 + (*((var_a3 * 2) + &D_800282D8) * *(0x801246E4 + temp_v1))) * temp_a0) / 128);
            var_s0->py = ((s32) ((temp_s2->unk18 + (*((temp_s2->unkE * 2) + &D_800286D8) * temp_s2->unk4)) * temp_a0) / 128) + 0x02600000;
            var_v0 = temp_s2->unk8 * temp_a0;
            if (var_v0 < 0) {
                var_v0 += 0x7F;
            }
            var_a1_2 += 1;
            var_a3 = (var_a3 + 0x40) & 0x1FF;
            var_s0->pz = (*((temp_s2->unk10 * 2) + &D_800286D8) * (var_v0 >> 7)) + 0xA00000;
            var_s0 = var_s0->unk284;
        } while (var_a1_2 != 8);
        var_fp = 0;
        sp38 = 0;
        temp_s2->unkC = (s16) (((u16) temp_s2->unkC + 2) & 0x1FF);
        temp_s3 = e->parent;
        temp_s6 = dir_from_delta(g_ent->px - temp_t0, (g_ent->py + 0x80000) - 0x02600000);
        if (temp_s3->hp == 0) {
            var_s0_2 = e;
            var_a1_3 = 0;
loop_11:
            var_a1_3 += 1;
            var_s0_2->flags &= ~3;
            var_s0_2 = var_s0_2->unk284;
            if (var_a1_3 != 8) {
                goto loop_11;
            }
        } else {
            temp_a0_2 = e->bytes[1];
            switch (temp_a0_2) {                    /* switch 1; irregular */
            case 0:                                 /* switch 1 */
                rel_tile(e, &sp20);
                var_fp = 1;
                if (!(g_mode_flags & 0x20) && (*(s32 *)0x801E6378 & 2)) {
                    if ((u32) (temp_s6 - 6) >= 0x15U) {
                        var_v0_2 = temp_s6 - 6;
                        if (sp24 < 5) {
                            if (sp20 < 5) {
                                e->bytes[1] = 1;
                                e->bytes[2] = 0;
                                e->ai[1] = 0x18;
                                e->delay = (*(&D_80023654 + (temp_s6 * 2)) * 0x2400) & 0xFFF80000;
                            } else {
                                var_v0_2 = temp_s6 - 6;
                                goto block_27;
                            }
                        } else {
block_27:
                            if ((var_v0_2 >= 0x15U) && (sp20 < 7) && (sp24 < 7)) {
                                e->bytes[1] = 3;
                                goto block_34;
                            }
                            goto block_31;
                        }
                    } else {
block_31:
                        if ((sp30 < 0) && ((((temp_s7 ^ 1) << 5) + 0x80120000)->unk4700 != 2)) {
                            e->bytes[1] = 2;
                            temp_s2->unk1C = 2;
block_34:
                            e->bytes[2] = 0;
                            e->ai[1] = 0x18;
                        }
                    }
                }
                break;
            case 1:                                 /* switch 1 */
                temp_v1_2 = e->bytes[2];
                if (temp_v1_2 != temp_a0_2) {
                    switch ((s32) temp_v1_2) {      /* switch 2; irregular */
                    case 0:                         /* switch 2 */
                        temp_v0_2 = (u16) e->ai[1];
                        var_v0_3 = temp_v0_2 - 1;
                        if (temp_v0_2 == 0) {
                            play_sound(0x19E);
                            e->ai[1] = 0x1A;
                            e->bytes[2] += 1;
                            temp_s2->unkE = 0x180;
                            temp_s2->unk4 = 0x3000;
                            temp_s2->unk10 = 0;
                        } else {
block_74:
                            e->ai[1] = var_v0_3;
                            temp_v1_3 = temp_s2->unk14;
                            if (temp_v1_3 != 0) {
                                var_v0_4 = 0xFFFF0000;
                                if (temp_s7 == 0) {
                                    var_v0_4 = 0x10000;
                                }
                                temp_s2->unk14 = (s32) (temp_v1_3 + var_v0_4);
                            }
                            temp_v1_4 = temp_s2->unk18;
                            if (temp_v1_4 != 0) {
                                temp_s2->unk18 = (s32) (temp_v1_4 + 0xFFFC0000);
                            }
                            temp_v0_3 = *(0x801246E4 + temp_v1);
                            if (temp_v0_3 != 0) {
                                *(0x801246E4 + temp_v1) = (s32) (temp_v0_3 - 0x80);
                            }
                        }
                        break;
                    case 2:                         /* switch 2 */
                        temp_v0_4 = (u16) e->ai[1] - 1;
                        e->ai[1] = temp_v0_4;
                        if (!(temp_v0_4 & 0xFFFF)) {
                            *(s32 *)0x801F94D0 = 0;
block_56:
                            e->bytes[2] += 1;
                            temp_v0_5 = temp_s3->hp_max;
                            if (temp_s3->hp < ((s32) (temp_v0_5 + ((u32) temp_v0_5 >> 0x1F)) >> 1)) {
block_129:
                                e->ai[1] = 0x46;
                            } else {
block_128:
                                e->ai[1] = 0x64;
                            }
                        }
                        break;
                    case 3:                         /* switch 2 */
                        temp_v0_6 = (u16) e->ai[1] - 1;
                        e->ai[1] = temp_v0_6;
                        if (temp_v0_6 & 0xFFFF) {
                            temp_v1_5 = temp_s2->unkE;
                            if (temp_v1_5 != 0x180) {
                                temp_s2->unkE = (s16) ((temp_v1_5 - 4) & 0x1FF);
                            }
                            temp_v0_7 = temp_s2->unk10;
                            if (temp_v0_7 != 0) {
                                temp_s2->unk10 = (s16) ((temp_v0_7 - 4) & 0x1FF);
                            }
                            temp_v1_6 = temp_s2->unk14;
                            temp_v0_8 = (&D_80026CF4)[temp_s7];
                            if (temp_v1_6 != temp_v0_8) {
                                if (temp_v1_6 < temp_v0_8) {
                                    var_v0_5 = temp_v1_6 + 0x40000;
                                } else {
block_98:
                                    var_v0_6 = 0xFFFC0000;
block_99:
                                    var_v0_5 = temp_s2->unk14 + var_v0_6;
                                }
                                temp_s2->unk14 = var_v0_5;
                            }
block_101:
                            temp_v1_7 = temp_s2->unk18;
                            if (temp_v1_7 != 0x200000) {
                                temp_s2->unk18 = (s32) (temp_v1_7 + 0x20000);
                            }
                            temp_v1_8 = *(0x801246E4 + temp_v1);
                            if (temp_v1_8 != 0x600) {
                                *(0x801246E4 + temp_v1) = (s32) (temp_v1_8 + 0x80);
                            }
                        } else {
block_131:
                            sp38 = 1;
                        }
                        break;
                    }
                } else {
                    temp_v0_9 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_9;
                    if (temp_v0_9 & 0xFFFF) {
                        temp_v1_9 = temp_s2->unk14;
                        if (temp_v1_9 < e->delay) {
                            temp_s2->unk14 = (s32) (temp_v1_9 + 0x80000);
                        }
                        if (e->delay < temp_s2->unk14) {
                            temp_s2->unk14 = (s32) (temp_s2->unk14 - 0x80000);
                        }
                        temp_v0_10 = temp_s2->unkE;
                        if (temp_v0_10 != 0) {
                            temp_s2->unkE = (s16) ((temp_v0_10 + 8) & 0x1FF);
                        }
                        temp_v1_10 = temp_s2->unk10;
                        if (temp_v1_10 != 0x80) {
                            temp_s2->unk10 = (s16) ((temp_v1_10 + 8) & 0x1FF);
                        }
                    } else {
                        e->ai[1] = 0x14;
                        e->bytes[2] += 1;
                        *(void *)0x801F94D0 = (s32) temp_a0_2;
                        *(s32 *)0x801F94DC = (s32) temp_a0_2;
                        *(s32 *)0x801F94E0 = (s32) temp_a0_2;
                        *(s32 *)0x801F94D4 = 2;
                        *(s32 *)0x801F94D8 = 2;
                    }
                }
                break;
            case 2:                                 /* switch 1 */
                temp_a1 = e->bytes[2];
                temp_v1_11 = temp_a1 & 0xFF;
                switch (temp_v1_11) {               /* switch 3; irregular */
                default:                            /* switch 3 */
                    if (temp_v1_11 != temp_a0_2) {
                        if (temp_v1_11 != 3) {

                        } else {
                            temp_v0_11 = (u16) e->ai[1] - 1;
                            e->ai[1] = temp_v0_11;
                            if (temp_v0_11 & 0xFFFF) {
                                temp_v1_12 = temp_s2->unk14;
                                temp_v0_12 = (&D_80026CF4)[temp_s7];
                                var_fp = 1;
                                if (temp_v1_12 != temp_v0_12) {
                                    var_v0_6 = 0x40000;
                                    if (temp_v1_12 >= temp_v0_12) {
                                        goto block_98;
                                    }
                                    goto block_99;
                                }
                                goto block_101;
                            }
                            goto block_131;
                        }
                    } else {
                        temp_v0_13 = (u16) e->ai[1];
                        var_v0_7 = temp_v0_13 - 1;
                        if (temp_v0_13 == 0) {
                            e->ai[1] = 0x14;
                            play_sound(0x19F);
                            temp_s0 = spawn_warp_entity(temp_s3, 1, 0xD0, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir);
                            spawn_effect(1, 0, 1, e->px, e->py, e->pz + 0x100000);
                            if (temp_s0 != NULL) {
                                temp_s0->target_anim = 0xF;
                                temp_s0->fz = 0x40000;
                                temp_s0->bytes[0] = 1;
                                temp_s0->flags &= ~1;
                                temp_v0_14 = e->delay + 1;
                                e->delay = temp_v0_14;
                                if (temp_v0_14 == 0xA) {
                                    goto block_56;
                                }
                            }
                        } else {
block_123:
                            e->ai[1] = var_v0_7;
                        }
                    }
                    break;
                case 0:                             /* switch 3 */
                    temp_v0_15 = (u16) e->ai[1];
                    var_v0_3 = temp_v0_15 - 1;
                    if (temp_v0_15 != 0) {
                        goto block_74;
                    }
                    e->bytes[2] = temp_a1 + 1;
                    e->ai[4] = 7;
                    e->delay = 0;
                    if (e->target_anim == 0) {
                        e->target_anim = 6;
                    } else {
                        e->target_anim = 5;
                    }
                    break;
                case 1:                             /* switch 3 */
                    var_s0_3 = e;
                    temp_v0_16 = (u16) e->ai[4];
                    var_a1_4 = 0;
                    if (temp_v0_16 != 0) {
                        do {
                            var_s0_3 = var_s0_3->unk284;
                            var_a1_4 += 1;
                        } while (var_a1_4 != temp_v0_16);
                    }
                    if (var_s0_3->target_anim == 8) {
                        if (var_s0_3->anim_done != 0) {
                            var_s0_3->target_anim = 7;
                            temp_v0_17 = (u16) e->ai[4] - 1;
                            e->ai[4] = temp_v0_17;
                            if (!(temp_v0_17 & 0xFFFF)) {
                                e->bytes[2] += 1;
                                var_v0_8 = e->pz + 0x100000;
block_119:
                                spawn_effect(1, 0, 0, e->px, M2C_ERROR(/* Unable to find stack arg 0x10 in block */), var_v0_8);
                            }
                        }
                    } else {
block_120:
                        var_s0_3->target_anim = 8;
                    }
                    break;
                }
                break;
            case 3:                                 /* switch 1 */
                temp_v1_13 = e->bytes[2];
                switch (temp_v1_13) {               /* switch 4; irregular */
                default:                            /* switch 4 */
                    if (temp_v1_13 != temp_a0_2) {

                    } else {
                        temp_v0_18 = (u16) e->ai[1] - 1;
                        e->ai[1] = temp_v0_18;
                        if (!(temp_v0_18 & 0xFFFF)) {
                            goto block_131;
                        }
                    }
                    break;
                case 0:                             /* switch 4 */
                    e->ai[4] = 7;
                    e->bytes[2] += 1;
                    break;
                case 1:                             /* switch 4 */
                    var_s0_3 = e;
                    temp_v0_19 = (u16) e->ai[4];
                    var_a1_5 = 0;
                    if (temp_v0_19 != 0) {
                        do {
                            var_s0_3 = var_s0_3->unk284;
                            var_a1_5 += 1;
                        } while (var_a1_5 != temp_v0_19);
                    }
                    if (var_s0_3->target_anim == 8) {
                        if (var_s0_3->anim_done != 0) {
                            var_s0_3->target_anim = 7;
                            temp_v0_20 = (u16) e->ai[4] - 1;
                            e->ai[4] = temp_v0_20;
                            if (!(temp_v0_20 & 0xFFFF)) {
                                e->bytes[2] += 1;
                                var_v0_8 = e->pz;
                                goto block_119;
                            }
                        }
                    } else {
                        goto block_120;
                    }
                    break;
                case 2:                             /* switch 4 */
                    temp_v0_21 = (u16) e->ai[1];
                    var_fp = 1;
                    if (temp_v0_21 != 0) {
                        var_v0_7 = temp_v0_21 - 1;
                        goto block_123;
                    }
                    e->ai[1] = 0xF;
                    temp_s4 = e->py + 0x80000;
                    temp_s5 = e->pz - 0x80000;
                    play_sound(0x19F);
                    temp_s0_2 = spawn_warp_entity(temp_s3, 1, 0xD0, e->px, /* extra? */ temp_s4, /* extra? */ temp_s5, /* extra? */ e->target_dir);
                    spawn_effect(1, 0, 1, e->px, e->py, e->pz);
                    if (temp_s0_2 != NULL) {
                        temp_s0_2->bytes[0] = 2;
                        temp_s0_2->target_anim = e->target_anim + 0xA;
                        temp_s0_2->flags = (temp_s0_2->flags & ~1) | 0x100;
                        temp_s0_2->bytes[1] = (u8) e->unk288 + 2;
                        temp_v0_22 = (u16) e->ai[4] + 1;
                        e->ai[4] = temp_v0_22;
                        if ((temp_v0_22 & 0xFFFF) == 5) {
                            e->bytes[2] += 1;
                            temp_v0_23 = temp_s3->hp_max;
                            if (temp_s3->hp >= ((s32) (temp_v0_23 + ((u32) temp_v0_23 >> 0x1F)) >> 1)) {
                                goto block_128;
                            }
                            goto block_129;
                        }
                    }
                    break;
                }
                break;
            }
            if (var_fp != 0) {
                if ((u32) (temp_s6 - 6) >= 0x15U) {
                    e->target_dir = temp_s6;
                }
                if ((temp_s6 < 2) || (temp_s6 == 0x1F)) {
                    e->target_anim = 0;
                } else {
                    var_v0_9 = 1;
                    if ((temp_s6 >= 4) && (var_v0_9 = 2, ((temp_s6 < 0x10) == 0))) {
                        if (temp_s6 >= 0x1D) {
                            var_v0_9 = 3;
                            goto block_143;
                        }
                        var_v0_9 = 4;
                        if (temp_s6 >= 0x11) {
                            goto block_143;
                        }
                    } else {
block_143:
                        e->target_anim = var_v0_9;
                    }
                }
            }
            if (sp38 != 0) {
                temp_s2->unk18 = 0x200000;
                *(0x801246E4 + temp_v1) = 0x600;
                temp_s2->unk4 = 0;
                temp_s2->unkE = 0;
                temp_s2->unk10 = 0;
                temp_s2->unk14 = (s32) (&D_80026CF4)[temp_s7];
                e->bytes[1] = 0;
                temp_s2->unk1C = 0;
            }
        }
    }
}
