/* 8007B5F0: built-in program C54 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_800832B0();                                  /* extern */
? func_80083394(struct Entity *);                   /* extern */
extern ? D_80027F98;

void AI_C54(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_11;
    s16 temp_v0_18;
    s16 var_v0_2;
    s32 *var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_s0;
    s32 temp_s0_3;
    s32 temp_s0_4;
    s32 temp_s2;
    s32 temp_s3;
    s32 temp_s3_2;
    s32 temp_v0;
    s32 temp_v0_13;
    s32 temp_v0_3;
    s32 temp_v0_4;
    s32 temp_v0_5;
    s32 temp_v0_8;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 temp_v1_8;
    s32 var_s0;
    s32 var_s0_2;
    s32 var_s0_3;
    s32 var_s0_4;
    s32 var_s0_5;
    s32 var_s0_6;
    s32 var_s2;
    s32 var_t3;
    s32 var_t3_2;
    s32 var_v0_3;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v1;
    s32 var_v1_2;
    struct Entity *temp_a0;
    struct Entity *temp_v0_12;
    struct Entity *temp_v0_14;
    struct Entity *temp_v0_15;
    struct Entity *temp_v0_17;
    struct Entity *temp_v0_19;
    struct Entity *temp_v0_2;
    u16 temp_v0_10;
    u16 temp_v0_6;
    u16 temp_v1_2;
    u32 temp_v0_7;
    u32 temp_v0_9;
    u8 temp_s0_2;
    u8 temp_v0_16;
    u8 temp_v1;
    void **var_v1_3;
    void **var_v1_4;
    void *temp_a3;
    void *temp_a3_2;
    void *temp_a3_3;

    if (*(s32 *)0x801F0074 == 0) {
        var_s0 = 0;
        var_v0 = (s32 *)0x801247FC;
        do {
            *var_v0 = 0;
            var_s0 += 1;
            var_v0 += 4;
        } while (var_s0 != 0xC);
        *(s32 *)0x8012483C = 0;
        *(s32 *)0x80124838 = 0;
        *(s32 *)0x80124834 = 0;
        *(s32 *)0x80124830 = 0;
        *(s32 *)0x8012482C = 0;
        *(void *)0x801F0074 = 1;
    }
    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394(e);
            return;
        }
        e->target_anim = 7;
        e->flags |= 0x40;
        return;
    }
    temp_v0 = *(void *)0x80124838;
    if (temp_v0 != 0) {
        *(void *)0x80124838 = (s32) (temp_v0 - 1);
    }
    rel_tile(e, &sp20);
    temp_v1_2 = (u16) e->ai[4];
    if (temp_v1_2 != 0) {
        e->delay = ((e->delay - temp_v1_2) + 0xC) & 0x1FF;
        if (e->unk284 == NULL) {
            if (*(s32 *)0x80124848 == 0x708) {
                temp_v0_2 = spawn_warp_entity(e, 0, 0x19, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ 0);
                e->unk284 = temp_v0_2;
                temp_v0_2->target_anim = 4;
                temp_v0_2->flags &= ~0x80;
            } else {
                temp_v1_3 = e->item_state + 0x1000;
                if ((((sp20 * 0x180000) - (temp_v1_3 * 0x300)) >= 0) || (var_s0_2 = 1, (((sp24 << 0x14) - (temp_v1_3 << 9)) >= 0))) {
                    var_s0_2 = 0;
                }
                if ((var_s0_2 == 0) && (sp20 < 6) && (sp24 < 6)) {
                    *(void *)0x80124848 = 0;
                    temp_v0_3 = e->item_state + 0x16;
                    e->item_state = temp_v0_3;
                    if (temp_v0_3 >= 0x1001) {
                        e->item_state = 0x1000;
                    }
                } else {
                    temp_v0_4 = e->item_state;
                    if ((temp_v0_4 != 0) || (var_s0_2 != 0)) {
                        temp_v0_5 = temp_v0_4 - 0x16;
                        e->item_state = temp_v0_5;
                        if (temp_v0_5 < 0) {
                            e->item_state = 0;
                        }
                    } else {
                        *(void *)0x80124848 = (s32) (*(void *)0x80124848 + 1);
                    }
                }
            }
        }
    } else {
        temp_a0 = e->unk284;
        if (temp_a0 != NULL) {
            remove_entity(temp_a0);
            e->unk284 = NULL;
        }
    }
    temp_v1_4 = e->target_anim;
    switch (temp_v1_4) {
    case 0:
        temp_v0_6 = (u16) e->ai[1];
        var_v0_2 = temp_v0_6 - 1;
        if (temp_v0_6 == 0) {
            if ((u16) e->ai[4] == 0) {
                e->target_anim = 4;
                e->bytes[0] = 0xFF;
                var_v0_2 = 0x17;
                goto block_108;
            }
            temp_s0 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            temp_v1_5 = *(void *)0x8012483C;
            if ((temp_v1_5 == 1) || ((temp_v1_5 != 2) && (sp24 < 7) && ((u32) (temp_s0 - 7) >= 0x13U) && (temp_lo = g_rng_seed * 0x7D2B89DD, g_rng_seed = temp_lo + 0xE06A02E7, (((temp_lo + 0xE06A02E7) / MULHI_3) == 0)))) {
                temp_v1_6 = *(void *)0x8012482C;
                e->target_anim = 8;
                *(void *)0x8012483C = 0;
                *(void *)0x80124830 = 0;
                if (temp_v1_6 == 0) {
                    var_t3 = g_rng_seed * 0x7D2B89DD;
                    var_v1 = 3;
                    goto block_44;
                }
                var_v0_3 = 9;
                if (temp_v1_6 != 6) {
                    var_t3 = g_rng_seed * 0x7D2B89DD;
                    var_v1 = 9;
block_44:
                    temp_v0_7 = var_t3 + 0xE06A02E7;
                    g_rng_seed = temp_v0_7;
                    var_v0_3 = (s32) MULTU_HI(temp_v0_7, var_v1) >> 0;
                }
                *(void *)0x80124834 = var_v0_3;
                if (*(void *)0x80124834 < 3) {
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    if (((temp_lo_2 + 0xE06A02E7) / MULHI_3) != 0) {
                        if ((u32) (temp_s0 - 2) >= 0x1DU) {
                            *(void *)0x80124834 = 0;
                        } else {
                            var_v0_4 = 1;
                            if (temp_s0 >= 7) {
                                var_v0_4 = 2;
                            }
                            *(void *)0x80124834 = var_v0_4;
                        }
                    }
                }
                temp_v0_8 = *(void *)0x8012482C + 1;
                *(void *)0x8012482C = temp_v0_8;
                if (temp_v0_8 == 7) {
                    *(void *)0x8012482C = 0;
                }
                e->target_dir = *((*(void *)0x80124830 * 4) + ((*(void *)0x80124834 * 0x18) + &D_80027F98));
                return;
            }
            if (*(void *)0x80124838 == 0) {
                *(void *)0x8012483C = 0;
                if (sp24 >= 5) {
                    var_t3_2 = g_rng_seed * 0x7D2B89DD;
                    var_v1_2 = 2;
                } else {
                    var_t3_2 = g_rng_seed * 0x7D2B89DD;
                    var_v1_2 = 6;
                }
                temp_v0_9 = var_t3_2 + 0xE06A02E7;
                g_rng_seed = temp_v0_9;
                e->bytes[0] = (u8) ((s32) MULTU_HI(temp_v0_9, var_v1_2) >> 0);
                e->target_anim = 4;
                e->ai[1] = 0x17;
                e->bytes[1] = 0;
                return;
            }
        } else {
block_108:
            e->ai[1] = var_v0_2;
        default:
            return;
        }
        break;
    case 4:
        temp_v0_10 = (u16) e->ai[1];
        temp_v0_11 = temp_v0_10 - 1;
        if (temp_v0_10 != 0) {
            e->ai[1] = temp_v0_11;
            if (!(temp_v0_11 & 0xFFFF)) {
                if (e->bytes[0] == 0xFF) {
                    var_s0_3 = 0;
                    e->ai[4] = 8;
                    e->item_state = 0;
                    e->delay = 0;
                    *(void *)0x80124848 = 0;
                    temp_s3 = e->pz + 0xC0000;
                    do {
                        temp_v0_12 = spawn_warp_entity(e, 1, 0xC2, 0, /* extra? */ 0, /* extra? */ temp_s3, /* extra? */ 0);
                        temp_v0_13 = var_s0_3 << 6;
                        var_s0_3 += 1;
                        temp_v0_12->delay = temp_v0_13;
                        temp_v0_12->target_anim = 1;
                    } while (var_s0_3 != 8);
                } else {
                    temp_s2 = e->py;
                    temp_s3_2 = e->pz + 0x200000;
                    temp_v0_14 = spawn_warp_entity(e, 1, 0xC0, e->px + 0xFFF60000, /* extra? */ temp_s2, /* extra? */ temp_s3_2, /* extra? */ 0);
                    if (temp_v0_14 != NULL) {
                        temp_v0_14->bytes[0] = e->bytes[1] * 2;
                    }
                    temp_v0_15 = spawn_warp_entity(e, 1, 0xC0, e->px + 0xA0000, /* extra? */ temp_s2, /* extra? */ temp_s3_2, /* extra? */ 0);
                    if (temp_v0_15 != NULL) {
                        temp_v0_15->bytes[0] = (e->bytes[1] * 2) + 1;
                    }
                    temp_v0_16 = e->bytes[1] + 1;
                    e->bytes[1] = temp_v0_16;
                    if ((temp_v0_16 & 0xFF) != 3) {
                        e->ai[1] = 0x1E;
                    }
                }
            }
        }
        if (e->anim_done != 0) {
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 134217728) + 0x1E;
            *(void *)0x80124838 = 0xF0;
            return;
        }
        break;
    case 8:
        if (e->anim_done != 0) {
            e->target_anim = 1;
            e->target_dir = *((*(void *)0x80124830 * 4) + ((*(void *)0x80124834 * 0x18) + &D_80027F98));
            return;
        }
        break;
    case 1:
        if (e->anim_done != 0) {
            temp_v1_7 = e->target_dir;
            *(void *)0x80124830 = (s32) (*(void *)0x80124830 + 1);
            if (temp_v1_7 == 0) {
                var_s0_4 = 0x150000;
                var_s2 = 0x260000;
                *(s32 *)0x80124840 = 0;
                var_v0_5 = 0x100000;
            } else {
                var_s0_4 = 0x3F0000;
                if (temp_v1_7 == 0x10) {
                    var_s0_4 = 0xFFE90000;
                    var_s2 = 0x170000;
                    *(void *)0x80124840 = 0xFFEA0000;
                    var_v0_5 = 0x160000;
                } else {
                    var_s2 = 0x170000;
                    var_v0_5 = 0x160000;
                    *(void *)0x80124840 = 0x160000;
                }
            }
            *(s32 *)0x80124844 = var_v0_5;
            func_800832B0();
            temp_v0_17 = spawn_warp_entity(e, 1, 0xBF, var_s0_4 + e->px, /* extra? */ (var_s2 + e->py), /* extra? */ e->pz, /* extra? */ e->target_dir);
            *(struct Entity **)0x801247FC = temp_v0_17;
            if (temp_v0_17 != NULL) {
                e->bytes[2] = 1;
                e->target_anim = 2;
                var_v0_2 = 0x12;
                goto block_108;
            }
        }
        break;
    case 2:
        temp_v0_18 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_18;
        if (!(temp_v0_18 & 0xFFFF)) {
            var_s0_5 = 0;
            var_v1_3 = (void **)0x801247FC;
            do {
                temp_a3 = *var_v1_3;
                var_s0_5 += 1;
                temp_a3->unk88 = 1;
                temp_a3->unk6C = (s32) (temp_a3->unk6C | 0x40);
                *var_v1_3 = NULL;
                var_v1_3 += 4;
            } while (var_s0_5 != 0xC);
            e->target_anim = 3;
            e->bytes[2] = 0;
            return;
        }
        temp_s0_2 = e->bytes[2];
        if (temp_s0_2 != 0xC) {
            temp_s0_3 = temp_s0_2 * 4;
            temp_a3_2 = (temp_s0_3 + 0x80120000)->unk47F8;
            temp_v0_19 = spawn_warp_entity(e, 1, 0xBF, temp_a3_2->unk114 + *(void *)0x80124840, /* extra? */ (temp_a3_2->unk118 + *(void *)0x80124844), /* extra? */ temp_a3_2->unk11C, /* extra? */ e->target_dir);
            (temp_s0_3 + 0x80120000)->unk47FC = temp_v0_19;
            if (temp_v0_19 != NULL) {
                e->bytes[2] += 1;
                return;
            }
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            temp_s0_4 = *((*(void *)0x80124830 * 4) + ((*(void *)0x80124834 * 0x18) + &D_80027F98));
            if (temp_s0_4 == -1) {
                e->target_anim = 9;
                return;
            }
            e->target_anim = 1;
            e->target_dir = temp_s0_4;
            return;
        }
        break;
    case 9:
        if (e->anim_done != 0) {
            temp_lo_4 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_4 + 0xE06A02E7;
            var_v0_2 = ((temp_lo_4 + 0xE06A02E7) / 134217728) + 0x3C;
            goto block_108;
        }
        break;
    case 6:
        var_s0_6 = 0;
        var_v1_4 = (void **)0x801247FC;
        do {
            temp_a3_3 = *var_v1_4;
            if (temp_a3_3 != NULL) {
                temp_a3_3->unk88 = 1;
                temp_a3_3->unk6C = (s32) (temp_a3_3->unk6C | 0x40);
                *var_v1_4 = NULL;
            }
            var_s0_6 += 1;
            var_v1_4 += 4;
        } while (var_s0_6 != 0xC);
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                return;
            }
            temp_v1_8 = *(void *)0x8012482C;
            if ((temp_v1_8 == 0) || (var_v0_6 = 2, (temp_v1_8 == 6))) {
                var_v0_6 = 1;
            }
            *(void *)0x8012483C = var_v0_6;
            e->damaged_tick = 0x5A;
            var_v0_2 = 0x14;
            e->target_anim = 0;
            goto block_108;
        }
        break;
    }
}
