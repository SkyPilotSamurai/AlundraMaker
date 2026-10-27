/* 800772D4: built-in program C48 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_80023654;
extern ? D_80023694;
extern ? D_80027BB4;
extern ? D_80027BD8;
extern ? D_80027BDC;

void AI_C48(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 *var_s2_2;
    s16 temp_v0_3;
    s16 temp_v0_6;
    s16 temp_v0_9;
    s32 *var_s2;
    s32 temp_a0;
    s32 temp_a1;
    s32 temp_a1_2;
    s32 temp_a2;
    s32 temp_a2_2;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_s1;
    s32 temp_t0;
    s32 temp_v0_4;
    s32 temp_v1_2;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 var_s3;
    s32 var_s3_2;
    s32 var_s3_3;
    s32 var_s4;
    s32 var_s6;
    s32 var_v0;
    s32 var_v1;
    s32 var_v1_2;
    struct Entity *temp_s1_2;
    struct Entity *temp_v0_10;
    struct Entity *temp_v0_11;
    struct Entity *temp_v0_2;
    struct Entity *temp_v0_7;
    struct Entity *var_s1;
    u16 temp_a0_2;
    u16 temp_v0;
    u16 temp_v0_5;
    u16 temp_v0_8;
    u32 temp_v1_3;
    u8 temp_v1;

    if (e->delay == 0) {
        var_s6 = 0;
        if (g_mode_flags & 0x20) {
            if (g_ent->touching != NULL) {
                g_ent->target_anim = 0x58;
                g_ent->target_dir = 0;
            } else if ((g_ent->target_anim == 0x58) && (g_ent->on_ground != 0)) {
                g_ent->damaged_tick = 0x78;
                g_ent->target_anim = 0;
                g_mode_flags &= ~0x20;
            }
        }
        temp_v1 = e->bytes[3];
        if ((temp_v1 != 0) && (e->target_anim == 0)) {
            if (temp_v1 < 4U) {
                func_80083394(e);
                return;
            }
            e->target_anim = 7;
            e->flags = (e->flags | 0x40) & ~0x100;
            e->pz += 0x200000;
            return;
        }
        rel_tile(e, &sp20);
        temp_v1_2 = e->target_anim;
        switch (temp_v1_2) {
        case 0:
            temp_v0 = (u16) e->ai[1];
            if (temp_v0 != 0) {
                e->ai[1] = temp_v0 - 1;
            } else {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                var_v0 = 1;
                if ((((temp_lo + 0xE06A02E7) / 2147483648) == 0) && (var_v0 = 1, (e->bytes[2] == 0))) {
                    e->target_anim = 5;
                    e->ai[1] = 0x1E;
                } else {
block_93:
                    e->target_anim = var_v0;
                }
            }
            break;
        case 1:
            if (e->anim_done != 0) {
                e->target_anim = 2;
                e->ai[1] = 0x708;
                *(struct Entity **)0x801247A0 = spawn_warp_entity(e, 1, 0xDD, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ 0);
                temp_v0_2 = spawn_warp_entity(e, 0, 0xEC, 0x03D80000, /* extra? */ 0x01480000, /* extra? */ e->pz, /* extra? */ 0);
                *(struct Entity **)0x801247A4 = temp_v0_2;
                if (temp_v0_2 != NULL) {
                    temp_v0_2->target_anim = 2;
                    temp_v0_2->flags |= 4;
                }
            }
            break;
        case 2:
            temp_v0_3 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_3;
            if (!(temp_v0_3 & 3)) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                temp_s1 = ((temp_lo_2 + 0xE06A02E7) / 2147483648) + 2;
                var_s3 = 0;
                if (temp_s1 != 0) {
                    do {
                        temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                        temp_v1_3 = temp_lo_3 + 0xE06A02E7;
                        temp_lo_4 = temp_v1_3 * 0x7D2B89DD;
                        g_rng_seed = temp_v1_3;
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        sp38 = temp_v1_3 * 0x31;
                        sp3C = (temp_lo_3 + 0xE06A02E7) / MULHI_49;
                        temp_a1 = e->item_state + 1;
                        temp_a0 = e->item_state * 8;
                        temp_a2 = e->item_state * 8;
                        e->item_state = temp_a1;
                        if (temp_a1 >= 9) {
                            e->item_state = 0;
                        }
                        var_s3 += 1;
                        spawn_warp_entity(e, 0, 0xEC, *(&D_80027BD8 + temp_a0) + (((temp_lo_3 + 0xE06A02E7) / MULHI_49) << 0x10), /* extra? */ (*(&D_80027BDC + temp_a2) + (((temp_lo_4 + 0xE06A02E7) / MULHI_33) << 0x10)), /* extra? */ e->pz, /* extra? */ 0)->fz = 0x8000;
                    } while (var_s3 != temp_s1);
                }
            }
            if ((u16) e->ai[1] == 0) {
                e->target_anim = 3;
                var_s6 = 1;
            } else {
                var_s4 = 0xB0;
                if (g_cur_map == 0x7B) {
                    var_s4 = 0xA0;
                }
                var_s3_2 = 0;
                var_s1 = g_ent;
                var_s2 = &g_ent->target_anim;
                do {
                    if ((var_s1 == g_ent) || (temp_v1_4 = var_s2->unk-20, (temp_v1_4 == 0x1DE)) || (temp_v1_4 == 2) || ((temp_v1_4 == 0xEC) && (var_s2->unk0 == 0)) || (temp_v1_4 == 0x1B2) || (temp_v1_4 == 0x112)) {
                        temp_a1_2 = var_s2->unk8C;
                        temp_a2_2 = var_s2->unk90;
                        temp_a3 = temp_a1_2 + 0xFC280000;
                        temp_t0 = temp_a2_2 + 0xFEC80000;
                        var_v1 = temp_a3;
                        if (temp_a3 < 0) {
                            var_v1 = -var_v1;
                        }
                        if (var_v1 <= 0x300000) {
                            var_v1_2 = temp_t0;
                            if (temp_t0 < 0) {
                                var_v1_2 = -var_v1_2;
                            }
                            if (var_v1_2 > 0x100000) {
                                goto block_46;
                            }
                            if (e->target_anim != 4) {
                                if ((var_s1 == g_ent) && !(g_ent->anim_flags & 0x40) && (g_ent->damaged_tick == 0)) {
                                    var_s6 = 1;
                                    g_ent->target_anim = 0x56;
                                    e->target_anim = 4;
                                    g_mode_flags |= 0x20;
                                    e->ai[1] = 0x9A;
                                    e->ai[4] = 1;
                                    g_ent->sfy = 0;
                                    g_ent->sfx = 0;
                                    g_ent->fy = 0;
                                    g_ent->fx = 0;
                                    g_ent->tfy = 0;
                                    g_ent->tfx = 0;
                                }
                                temp_v1_5 = var_s2->unk-20;
                                if ((temp_v1_5 == 0x1B2) || (temp_v1_5 == 0x112)) {
                                    var_s6 = 1;
                                    var_s2->unk0 = 0x12;
                                    e->target_anim = 4;
                                    e->ai[1] = 0x9A;
                                    e->ai[4] = 2;
                                }
                            }
                        } else {
block_46:
                            temp_v0_4 = dir_from_delta(0x03D80000 - temp_a1_2, 0x01380000 - temp_a2_2) * 2;
                            var_s2->unk44 = (s32) (*(&D_80023654 + temp_v0_4) * var_s4);
                            var_s2->unk48 = (s32) (*(&D_80023694 + temp_v0_4) * var_s4);
                        }
                    }
                    var_s3_2 += 1;
                    var_s2 += 0x294;
                    var_s1 += 0x294;
                } while (var_s3_2 != 0x40);
            }
            break;
        case 3:
            if (e->anim_done != 0) {
                e->target_anim = 0;
                e->ai[1] = 0x78;
                e->bytes[0] = 0;
            }
            break;
        case 4:
            temp_v0_5 = (u16) e->ai[1];
            temp_v0_6 = temp_v0_5 - 1;
            if (temp_v0_5 != 0) {
                e->ai[1] = temp_v0_6;
                if (!(temp_v0_6 & 0xFFFF)) {
                    play_sound(0xB2);
                    temp_v0_7 = spawn_warp_entity(e, 0, 0xEC, g_ent->px, /* extra? */ (g_ent->py + 0xFFFF0000), /* extra? */ g_ent->pz, /* extra? */ 0);
                    if (temp_v0_7 != NULL) {
                        temp_v0_7->target_anim = 1;
                        temp_v0_7->flags |= 2;
                        temp_a0_2 = (u16) e->ai[4];
                        if (temp_a0_2 == 1) {
                            g_ent->target_dir = 0x10;
                            g_ent->target_anim = 0;
                            g_ent->pz = e->pz;
                            temp_v0_7->px = g_ent->px;
                            temp_v0_7->py = g_ent->py;
                            temp_v0_7->pz = g_ent->pz;
                        } else if (temp_a0_2 == 2) {
                            if (g_cur_map == 0x7B) {
                                select(e, 7);
                            } else {
                                select(e, 1);
                                temp_v0_7->target_anim = 3;
                            }
                            temp_s1_2 = *(struct Entity **)0x8013D488;
                            temp_s1_2->pz = e->pz;
                            temp_s1_2->target_anim = 0x10;
                            temp_s1_2->ai[1] = 0x1E;
                            temp_s1_2->target_dir = 0;
                            temp_s1_2->bytes[2] = 1;
                        }
                        e->ai[4] = 0;
                    } else {
                        e->ai[1] = 1;
                    }
                }
            }
            if (e->anim_done != 0) {
                e->target_anim = 3;
                e->ai[1] = 0x78;
            }
            break;
        case 5:
            temp_v0_8 = (u16) e->ai[1];
            temp_v0_9 = temp_v0_8 - 1;
            if (temp_v0_8 != 0) {
                e->ai[1] = temp_v0_9;
                if (!(temp_v0_9 & 0xFFFF)) {
                    play_sound(0xB2);
                    temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                    var_s3_3 = 0;
                    g_rng_seed = temp_lo_5 + 0xE06A02E7;
                    var_s2_2 = (((temp_lo_5 + 0xE06A02E7) / MULHI_3) * 0xC) + &D_80027BB4;
                    do {
                        temp_v0_10 = spawn_warp_entity(e, 1, 0xDE, e->px, /* extra? */ (e->py + 0x1E0000), /* extra? */ (e->pz + 0xA0000), /* extra? */ (s32) *var_s2_2);
                        if (temp_v0_10 != NULL) {
                            e->bytes[2] += 1;
                            temp_v0_10->target_anim = var_s3_3 + 9;
                        }
                        var_s3_3 += 1;
                        var_s2_2 += 2;
                    } while (var_s3_3 != 6);
                }
            } else if (e->anim_done != 0) {
                temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 0;
                g_rng_seed = temp_lo_6 + 0xE06A02E7;
                e->ai[1] = ((temp_lo_6 + 0xE06A02E7) / MULHI_61) + 0x3C;
            }
            break;
        case 6:
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    var_s6 = 1;
                    e->ai[1] = 0x12C;
                    e->ai[5] = 0x1E;
                    e->target_anim = 0;
                    e->flags &= ~3;
                } else {
                    if (g_cur_map == 0x7B) {
                        if ((u8) e->bytes[0] < 2U) {
                            var_v0 = 2;
                            goto block_93;
                        }
                        goto block_90;
                    }
                    var_v0 = 2;
                    if ((u8) e->bytes[0] >= 3U) {
block_90:
                        e->target_anim = 3;
                        var_s6 = 1;
                        if ((g_cur_map == 0x7B) && ((u8) e->bytes[1] >= 0x14U)) {
                            select(e, 6);
                            remove_entity(*(void *)0x8013D488);
                            e->delay = 1;
                        }
                    } else {
                        goto block_93;
                    }
                }
            }
            break;
        }
        if (var_s6 != 0) {
            temp_v0_11 = *(void *)0x801247A0;
            temp_v0_11->target_anim = 2;
            temp_v0_11->flags |= 0x40;
            remove_entity(*(void *)0x801247A4);
        }
    }
}
