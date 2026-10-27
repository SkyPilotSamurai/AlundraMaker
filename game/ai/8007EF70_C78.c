/* 8007EF70: built-in program C78 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
? func_8003A534(struct Entity *, s8, s8, s8, s32, s32, s32); /* extern */
extern ? D_800281D4;
extern ? D_80028234;
extern ? D_800282D8;
extern ? D_800286D8;
extern ? D_80028AF8;

void AI_C78(struct Entity *e) {
    s32 sp20;
    s32 sp24;
    s16 temp_v0_11;
    s16 temp_v0_13;
    s16 temp_v0_8;
    s16 var_s3;
    s16 var_v0;
    s32 *var_s3_2;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a0_4;
    s32 temp_a0_5;
    s32 temp_lo;
    s32 temp_lo_10;
    s32 temp_lo_11;
    s32 temp_lo_12;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_lo_9;
    s32 temp_v0_10;
    s32 temp_v0_15;
    s32 temp_v0_16;
    s32 temp_v0_17;
    s32 temp_v0_7;
    s32 temp_v1;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 var_s2;
    s32 var_s2_2;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_4;
    struct Entity *temp_v0_12;
    struct Entity *temp_v0_14;
    struct Entity *temp_v0_2;
    struct Entity *temp_v0_3;
    struct Entity *temp_v0_4;
    struct Entity *temp_v0_6;
    u16 temp_v0;
    u16 temp_v0_9;
    u32 temp_a0;
    u32 temp_a1;
    u32 temp_a2;
    u32 temp_t2;
    u32 temp_v0_5;
    u32 temp_v1_4;
    u8 *temp_s4;
    u8 temp_v1_2;
    u8 temp_v1_3;
    u8 temp_v1_5;

    temp_s4 = g_ent->header_addr + 0x18;
    if ((e->bytes[0] == 1) && ((*(struct Entity **)0x801248D8)->bytes[1] == 2)) {
        if (e->target_anim == 8) {
            remove_entity(e);
        }
        if ((e->target_anim == 0) || (e->target_anim == 5)) {
            play_sound(0x120);
            e->target_anim = 4;
        }
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 8:                                         /* switch 1 */
        temp_v0 = (u16) e->ai[1];
        var_v0 = temp_v0 - 1;
        if (temp_v0 == 0) {
            if ((u32) (e->bytes[0] - 2) < 2U) {
                play_sound(0x121);
                e->target_anim = 0xD;
                temp_v0_2 = spawn_warp_entity(e, 1, 0xC4, e->px, /* extra? */ (e->py + 0x10000), /* extra? */ e->pz, /* extra? */ 0);
                if (temp_v0_2 != NULL) {
                    temp_v0_2->target_anim = 0xC;
                    temp_v0_2->contents_item = 0;
                    temp_v0_2->bi_c = 0x4E;
                }
            } else {
                temp_v1_2 = e->bytes[1];
                if (temp_v1_2 == 1) {
                    play_sound(0x122);
                    e->target_anim = 5;
                } else if ((temp_v1_2 == 9) && (*(s32 *)0x801248F0 == 0)) {
                    e->bytes[1] = 0;
                    e->ai[1] = 0x78;
                } else {
                    temp_v1_3 = e->bytes[1];
                    if (temp_v1_3 == 0xA) {
                        e->bytes[1] = 9;
                        temp_lo = g_rng_seed * 0x7D2B89DD;
                        temp_a1 = temp_lo + 0xE06A02E7;
                        *(void *)0x801248F0 = 0;
                        g_rng_seed = temp_a1;
                        var_s2 = 0;
                        if (((temp_lo + 0xE06A02E7) / MULHI_3) != 0) {
                            var_s3 = 0xA;
                            do {
                                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                                temp_lo_3 = (temp_lo_2 + 0xE06A02E7) * 0x7D2B89DD;
                                temp_t2 = temp_lo_3 + 0xE06A02E7;
                                g_rng_seed = temp_t2;
                                sp20 = temp_t2 * 7;
                                sp24 = (temp_lo_3 + 0xE06A02E7) / MULHI_7;
                                temp_v0_3 = spawn_warp_entity(e, 1, 0xC4, (((temp_lo_2 + 0xE06A02E7) / MULHI_7) * 0x180000) + 0xC00000, /* extra? */ ((((temp_lo_3 + 0xE06A02E7) / MULHI_7) << 0x14) + 0xB00000), /* extra? */ e->pz, /* extra? */ 0);
                                if (temp_v0_3 != NULL) {
                                    temp_v0_3->target_anim = 8;
                                    temp_v0_3->bi_c = 0x4E;
                                    temp_v0_3->bytes[0] = 2;
                                    temp_v0_3->ai[1] = var_s3;
                                    temp_v0_3->contents_item = 0;
                                    temp_v0_3->flags |= 0x2000;
                                    *(void *)0x801248F0 = (s32) (*(void *)0x801248F0 + 1);
                                }
                                var_s2 += 1;
                                var_s3 += 0x28;
                            } while (var_s2 != 3);
                        } else {
                            temp_lo_4 = temp_a1 * 0x7D2B89DD;
                            g_rng_seed = temp_lo_4 + 0xE06A02E7;
                            var_s3_2 = (((temp_lo_4 + 0xE06A02E7) / 2147483648) * 0xC) + &D_80028234;
                            do {
                                temp_v0_4 = spawn_warp_entity(e, 1, 0xC4, g_ent->px, /* extra? */ g_ent->py, /* extra? */ g_ent->floor, /* extra? */ *var_s3_2);
                                if (temp_v0_4 != NULL) {
                                    func_8003A534(temp_v0_4, (s8) temp_s4->unk0, temp_s4->unk1, temp_v0_4->header_addr->unk1A, (s32) temp_s4->unk3, (s32) temp_s4->unk4, (s32) temp_v0_4->header_addr->unk1D);
                                    temp_v0_4->target_anim = 9;
                                    temp_v0_4->bi_c = 0x4E;
                                    temp_v0_4->ai[1] = 0x1E;
                                    temp_v0_4->bytes[0] = 3;
                                    temp_v0_4->contents_item = 0;
                                    temp_v0_4->pz = g_ent->floor;
                                    temp_v0_4->flags |= 0x2000;
                                    *(void *)0x801248F0 = (s32) (*(void *)0x801248F0 + 1);
                                }
                                var_s2 += 1;
                                var_s3_2 += 4;
                            } while (var_s2 != 3);
                        }
                    } else if (temp_v1_3 == 0) {
                        temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                        temp_a2 = temp_lo_5 + 0xE06A02E7;
                        g_rng_seed = temp_a2;
                        temp_lo_6 = temp_a2 * 0x7D2B89DD;
                        if (((temp_lo_5 + 0xE06A02E7) / 2147483648) != 0) {
                            temp_v0_5 = temp_lo_6 + 0xE06A02E7;
                            temp_lo_7 = temp_v0_5 * 0x7D2B89DD;
                            g_rng_seed = temp_v0_5;
                            sp20 = temp_v0_5 * 5;
                            sp24 = (temp_lo_6 + 0xE06A02E7) / MULHI_5;
                            g_rng_seed = temp_lo_7 + 0xE06A02E7;
                            e->px = (((temp_lo_6 + 0xE06A02E7) / MULHI_5) * 0x180000) + 0xD80000;
                            e->py = (((temp_lo_7 + 0xE06A02E7) / MULHI_5) << 0x14) + 0xC00000;
                            play_sound(0x122);
                            e->bytes[1] = 3;
                            e->target_anim = 5;
                            e->target_dir = 0;
                            e->ai[1] = 2;
                        } else {
                            *(s32 *)0x801248E4 = 0;
                            *(s32 *)0x801248E8 = 0x2800;
                            e->bytes[2] = 0;
                            e->ai[4] = 0;
                            temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                            temp_v1_4 = temp_lo_8 + 0xE06A02E7;
                            temp_lo_9 = temp_v1_4 * 0x7D2B89DD;
                            temp_a0 = temp_lo_9 + 0xE06A02E7;
                            temp_lo_10 = temp_a0 * 0x7D2B89DD;
                            *(void *)0x801248D8 = e;
                            *(void *)0x801248F0 = 0;
                            g_rng_seed = temp_v1_4;
                            g_rng_seed = temp_a0;
                            g_rng_seed = temp_lo_10 + 0xE06A02E7;
                            sp20 = temp_a0 * 3;
                            sp24 = (temp_lo_9 + 0xE06A02E7) / MULHI_3;
                            *(s32 *)0x801248EC = (temp_lo_8 + 0xE06A02E7) / 536870912;
                            *(s32 *)0x801248F4 = (temp_lo_9 + 0xE06A02E7) / MULHI_3;
                            e->item_state = ((temp_lo_10 + 0xE06A02E7) / 2147483648) + 1;
loop_34:
                            temp_a0_2 = *(void *)0x801248EC;
                            if (temp_a0_2 != *(void *)0x801248F0) {
                                temp_v0_6 = spawn_warp_entity(e, 1, 0xC4, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ 0);
                                temp_v0_6->bytes[0] = 1;
                                temp_v0_6->bytes[1] = 1;
                                temp_a0_3 = *(void *)0x801248F0;
                                temp_v0_6->bi_c = 0x4E;
                                temp_v0_6->target_anim = 8;
                                temp_v0_6->bi_d = 0x23;
                                temp_v0_6->ai[1] = temp_a0_3 * 0x10;
                                temp_v0_6->delay = *((temp_a0_3 * 4) + ((*(void *)0x801248F4 << 5) + &D_800281D4)) & 0x1FF;
                            } else {
                                e->bytes[1] = 1;
                                e->ai[1] = temp_a0_2 * 0x10;
                                e->delay = *((temp_a0_2 * 4) + ((*(void *)0x801248F4 << 5) + &D_800281D4)) & 0x1FF;
                            }
                            temp_v0_7 = *(void *)0x801248F0 + 1;
                            *(void *)0x801248F0 = temp_v0_7;
                            if (temp_v0_7 != 8) {
                                goto loop_34;
                            }
                        }
                    }
                }
            }
        } else {
block_45:
            e->ai[1] = var_v0;
        }
        break;
    case 9:                                         /* switch 1 */
        if ((u32) (e->bytes[0] - 2) < 2U) {
            temp_v0_8 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_8;
            if (!(temp_v0_8 & 0xFFFF)) {
                e->target_anim = 8;
                e->ai[1] = 1;
                e->target_dir = (e->target_dir + 0x10) & 0x1F;
            } else if (e->force_adjusted != 0) {
                remove_entity(e);
                *(void *)0x801248F0 = (s32) (*(void *)0x801248F0 - 1);
            }
        }
        break;
    case 0:                                         /* switch 1 */
        temp_v0_9 = (u16) e->ai[1];
        var_v0 = temp_v0_9 - 1;
        if (temp_v0_9 != 0) {
            goto block_45;
        }
        temp_v1_5 = e->bytes[1];
        switch (temp_v1_5) {                        /* switch 2 */
        case 3:                                     /* switch 2 */
            temp_lo_11 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_11 + 0xE06A02E7;
            e->target_dir = (s32) *(((temp_lo_11 + 0xE06A02E7) / 1073741824) + &D_80028AF8);
            /* fallthrough */
        case 4:                                     /* switch 2 */
        case 5:                                     /* switch 2 */
        case 6:                                     /* switch 2 */
        case 7:                                     /* switch 2 */
            temp_lo_12 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_12 + 0xE06A02E7;
            temp_v0_10 = (temp_lo_12 + 0xE06A02E7) / 2147483648;
            temp_a0_4 = e->target_dir;
            if ((temp_a0_4 == 0) || (var_v0_2 = 0x10, (temp_a0_4 == 0x10))) {
                var_v0_2 = 0x18;
                if (temp_v0_10 == 0) {
                    var_v0_2 = 8;
                }
                goto block_55;
            }
            if (temp_v0_10 != 0) {
                e->target_dir = 0;
            } else {
block_55:
                e->target_dir = var_v0_2;
            }
            e->bytes[1] += 1;
            play_sound(0x11F);
            e->target_anim = 0xF;
            e->ai[1] = 0x1E;
            break;
        case 8:                                     /* switch 2 */
            e->bytes[1] = 0;
            break;
        case 0:                                     /* switch 2 */
block_68:
            play_sound(0x120);
            e->target_anim = 4;
            break;
        }
        break;
    case 4:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[0] == 0) {
                e->target_anim = 8;
                e->ai[1] = 0x78;
                e->bytes[1] = 0xA;
            } else {
block_76:
                remove_entity(e);
            }
        }
        break;
    case 3:                                         /* switch 1 */
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 0;
        }
        break;
    case 7:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[1] == 1) {
                e->bytes[1] = 2;
            }
            if (e->bytes[3] != 0) {
                e->contents_item = 0;
                e->target_anim = 2;
                e->flags |= 0x40;
            } else {
                goto block_68;
            }
        }
        break;
    case 15:                                        /* switch 1 */
        temp_v0_11 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_11;
        if (!(temp_v0_11 & 3)) {
            temp_v0_12 = spawn_warp_entity(e, 1, 0xC4, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir);
            if (temp_v0_12 != NULL) {
                temp_v0_12->target_anim = 0xB;
                temp_v0_12->bi_c = 0x4E;
            }
        }
        if (((u16) e->ai[1] == 0) || (e->force_adjusted != 0)) {
            e->target_anim = 0;
            e->ai[1] = 0xA;
        }
        break;
    case 11:                                        /* switch 1 */
    case 12:                                        /* switch 1 */
    case 14:                                        /* switch 1 */
        if (e->anim_done != 0) {
            goto block_76;
        }
        break;
    case 13:                                        /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 0x10;
            if (e->bytes[0] == 2) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            }
        }
        break;
    case 16:                                        /* switch 1 */
        temp_v0_13 = (u16) e->ai[1] + 1;
        e->ai[1] = temp_v0_13;
        if (!(temp_v0_13 & 7)) {
            temp_v0_14 = spawn_warp_entity(e, 1, 0xC4, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir);
            if (temp_v0_14 != NULL) {
                temp_v0_14->target_anim = 0xE;
                temp_v0_14->bi_c = 0x4E;
                func_8003A534(temp_v0_14, (s8) temp_s4->unk0, temp_s4->unk1, temp_v0_14->header_addr->unk1A, (s32) temp_s4->unk3, (s32) temp_s4->unk4, (s32) temp_v0_14->header_addr->unk1D);
                temp_v0_14->pz = g_ent->floor;
            }
        }
        if ((e->force_adjusted != 0) || (g_ent->touching == e)) {
            *(void *)0x801248F0 = (s32) (*(void *)0x801248F0 - 1);
            destroy_entity(e, -1);
        }
        break;
    }
    if ((u32) (e->bytes[1] - 1) < 2U) {
        if ((u16) (*(void *)0x801248D8)->ai[4] == 3) {
            play_sound(0x120);
            e->target_anim = 4;
        }
        if (*(void *)0x801248D8 == e) {
            temp_v0_15 = (*(void *)0x801248E4 - 4) & 0x1FF;
            *(void *)0x801248E4 = temp_v0_15;
            if (temp_v0_15 == 0) {
                e->ai[4] = (u16) e->ai[4] + 1;
            }
            temp_v1_6 = *(void *)0x801248E4 * 2;
            *(s32 *)0x801248DC = (*(&D_800282D8 + temp_v1_6) << 0xB) + 0x01080000;
            *(s32 *)0x801248E0 = (*(&D_800286D8 + temp_v1_6) << 0xB) + 0xE00000;
            if (e->bytes[2] == 0) {
                if ((u16) e->ai[4] == e->item_state) {
                    play_sound(0x122);
                    e->bytes[2] = 1;
                }
                if (e->bytes[2] != 0) {
                    goto block_96;
                }
            } else {
block_96:
                if (e->bytes[2] == 1) {
                    var_v0_3 = *(void *)0x801248E8 - 0x80;
                } else {
                    var_v0_3 = *(void *)0x801248E8 + 0x80;
                }
                *(void *)0x801248E8 = var_v0_3;
                if (*(void *)0x801248E8 == 0x1200) {
                    e->bytes[2] = 2;
                }
                if (*(void *)0x801248E8 == 0x2800) {
                    e->bytes[2] = 0;
                }
            }
        }
        temp_a0_5 = *(void *)0x801248E8;
        temp_v0_16 = (e->delay + 2) & 0x1FF;
        e->delay = temp_v0_16;
        e->px = *(void *)0x801248DC + (*(&D_800282D8 + (temp_v0_16 * 2)) * temp_a0_5);
        temp_v1_7 = e->target_anim;
        e->py = *(void *)0x801248E0 + (*(&D_800286D8 + (e->delay * 2)) * temp_a0_5);
        if ((temp_v1_7 == 0) || (temp_v1_7 == 8)) {
            temp_v0_17 = e->delay;
            var_s2_2 = temp_v0_17 >> 4;
            if (temp_v0_17 < 0) {
                var_s2_2 = (s32) (temp_v0_17 + 0xF) >> 4;
            }
            var_v0_4 = 8;
            if ((u32) (var_s2_2 - 4) >= 8U) {
                if ((u32) (var_s2_2 - 0xC) < 8U) {
                    e->target_dir = 0;
                    return;
                }
                var_v0_4 = 0x18;
                if ((u32) (var_s2_2 - 0x14) >= 8U) {
                    var_v0_4 = 0x10;
                }
                goto block_112;
            }
block_112:
            e->target_dir = var_v0_4;
        }
    }
}
