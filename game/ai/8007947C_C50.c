/* 8007947C: built-in program C50 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80027CD4;
extern ? D_80027CE0;
extern ? D_80027CEC;
extern ? D_80027DC4;
extern ? D_80027DC6;

void AI_C50(struct Entity *e) {
    s32 sp20;
    s32 sp48;
    s32 sp4C;
    s16 temp_a0_2;
    s16 temp_a2;
    s16 temp_v0_3;
    s16 temp_v0_4;
    s16 temp_v0_5;
    s16 var_s3;
    s16 var_v0_2;
    s16 var_v0_3;
    s16 var_v0_4;
    s16 var_v0_5;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_v0;
    s32 temp_v0_10;
    s32 temp_v0_2;
    s32 temp_v0_7;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 var_s1;
    s32 var_s1_3;
    s32 var_s2;
    s32 var_s2_2;
    s32 var_s2_3;
    s32 var_t1;
    s32 var_t4;
    s32 var_t4_2;
    s32 var_v0;
    struct Effect *temp_a0;
    struct Effect *temp_v0_6;
    struct Entity *temp_v0_8;
    u16 temp_v0_11;
    u16 temp_v0_9;
    u32 temp_t2;
    u32 temp_v1_6;
    void *var_s1_2;

    if (*(s32 *)0x801F0074 == 0) {
        *(struct Effect **)0x801247D8 = spawn_effect(1, 1, 0, e->px, e->py, e->pz);
        *(void *)0x801F0074 = 1;
        e->item_state = 0x78;
        *(s16 *)0x801247E0 = 0;
        *(s16 *)0x801247DC = 0;
    }
    temp_a0 = *(void *)0x801247D8;
    temp_a0->x = e->px;
    temp_a0->y = e->py;
    temp_a0->z = e->pz + 0x400000;
    if ((e->bytes[0] == 0) && (e->tile_y >= 0x19)) {
        e->bytes[0] = 1;
        e->target_anim = 0xA;
        e->ai[1] = 0x1E;
    }
    if ((e->bytes[0] == 1) && (e->tile_y >= 0x35)) {
        e->bytes[0] = 2;
        e->target_anim = 0xB;
        *(s32 *)0x801F94D0 = 0;
        e->delay = 0;
    }
    temp_v0 = e->delay;
    temp_v0_2 = temp_v0 - 1;
    if (temp_v0 != 0) {
        e->delay = temp_v0_2;
        if (temp_v0_2 == 0) {
            *(void *)0x801F94D0 = 0;
        }
    }
    temp_a0_2 = *(void *)0x801247DC;
    if ((temp_a0_2 != 0) || (*(void *)0x801247E0 != 0)) {
        var_s2 = 0;
        if (temp_a0_2 != 0) {
            temp_v0_3 = temp_a0_2 - 1;
            *(void *)0x801247DC = temp_v0_3;
            var_s2 = (temp_v0_3 << 0x10) == 0;
        } else {
            temp_v0_4 = *(void *)0x801247E0;
            if (temp_v0_4 != 0) {
                temp_v0_5 = temp_v0_4 - 1;
                *(void *)0x801247E0 = temp_v0_5;
                if ((temp_v0_5 << 0x10) == 0) {
                    var_s2 = 1;
                }
            }
        }
        if (var_s2 != 0) {
            *(void *)0x801F94D0 = 1;
            *(s32 *)0x801F94DC = 1;
            *(s32 *)0x801F94E0 = 1;
            *(s32 *)0x801F94D4 = 2;
            *(s32 *)0x801F94D8 = 2;
            e->delay = 0x1E;
        }
    }
    temp_v1 = e->delay;
    if ((temp_v1 == 0x1E) || (temp_v1 == 0x19) || (temp_v1 == 0x14)) {
        var_s1 = 0;
        var_v0 = 0 & 1;
        do {
            var_t4 = 0x01E00000;
            if (var_v0 != 0) {
                var_t4 = 0xF00000;
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            temp_v1_2 = temp_lo + 0xE06A02E7;
            temp_lo_2 = temp_v1_2 * 0x7D2B89DD;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            sp48 = temp_v1_2 * 0xB;
            sp4C = (temp_lo + 0xE06A02E7) / MULHI_11;
            temp_v0_6 = spawn_effect(0, 0x16, 1, var_t4 + (((temp_lo + 0xE06A02E7) / MULHI_11) * 0xC0000), g_ent->py + ((((temp_lo_2 + 0xE06A02E7) / MULHI_19) << 0x13) + 0xFFC00000), 0xA00000);
            if (temp_v0_6 != NULL) {
                temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_3 + 0xE06A02E7;
                temp_v0_6->vz = (((temp_lo_3 + 0xE06A02E7) / MULHI_5) << 0xE) + 0xFFFC0000;
            }
            var_s1 += 1;
            var_v0 = var_s1 & 1;
        } while (var_s1 != 2);
    }
    if ((u16) e->ai[4] < 0xDU) {
        if (e->target_anim != 8) {
            temp_v0_7 = e->item_state - 1;
            e->item_state = temp_v0_7;
            if (temp_v0_7 == 0) {
                e->item_state = 0xB4;
                if ((g_ent->tile_y - e->tile_y) >= 0xF) {
                    e->item_state = 0x78;
                }
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                var_s2_2 = 0;
                var_s3 = 0;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                var_s1_2 = (((temp_lo_4 + 0xE06A02E7) / MULHI_9) * 0x18) + &D_80027CEC;
loop_35:
                if (((g_ent->tile_y - e->tile_y) >= 5) || ((u16) e->ai[4] < 4U)) {
                    if (var_s2_2 != 0xC) {
                        temp_a2 = var_s1_2->unk4;
                        if (temp_a2 != 0) {
                            var_t4_2 = (var_s1_2->unk0 * 0x180000) + 0x01500000;
                            var_t1 = g_ent->py + (var_s1_2->unk2 << 0x14);
                            if (temp_a2 != 0x1F0) {
                                var_t4_2 += 0xC0000;
                                var_t1 += 0x80000;
                            }
                            if (var_t1 <= 0x033FFFFF) {
                                temp_v0_8 = spawn_warp_entity(e, 1, temp_a2 - 0x100, var_t4_2, /* extra? */ var_t1, /* extra? */ (e->pz + 0xA00000), /* extra? */ 0);
                                if (temp_v0_8 != NULL) {
                                    temp_v0_8->target_anim = 5;
                                    temp_v0_8->ai[1] = var_s3;
                                    e->ai[4] = (u16) e->ai[4] + 1;
                                }
                                var_s1_2 += 6;
                                var_s2_2 += 3;
                                var_s3 += 0x14;
                                goto loop_35;
                            }
                        }
                    }
                }
            }
        }
    }
    rel_tile(e, &sp20);
    temp_v1_3 = e->target_anim;
    var_s1_3 = 0;
    switch (temp_v1_3) {
    case 2:
    case 3:
    case 4:
        if ((e->force_adjusted == 0) || (var_v0_2 = 0x8C, (e->x_collision != g_ent))) {
            var_s1_3 = 1;
            if (e->anim_done != 0) {
            case 0:
                temp_v0_9 = (u16) e->ai[1];
                var_v0_3 = temp_v0_9 - 1;
                if (temp_v0_9 == 0) {
                    if ((g_ent->tile_y - e->tile_y) >= 0xF) {
                        var_v0_4 = 4;
                    } else {
                        temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                        var_v0_4 = *(&D_80027CD4 + (((temp_lo_5 + 0xE06A02E7) / MULHI_5) * 2));
                        g_rng_seed = temp_lo_5 + 0xE06A02E7;
                    }
                    e->target_anim = (s32) var_v0_4;
                    temp_v1_4 = e->target_anim;
                    e->cur_anim = -1;
                    if (temp_v1_4 != 0) {
                        var_s2_3 = temp_v1_4 - 2;
block_68:
                        temp_v0_10 = var_s2_3 * 4;
                        *(void *)0x801247DC = (s16) *(&D_80027DC4 + temp_v0_10);
                        *(void *)0x801247E0 = (s16) *(&D_80027DC6 + temp_v0_10);
                    } else {
block_67:
                        e->ai[1] = 0x1E;
                    }
                } else {
block_62:
                    e->ai[1] = var_v0_3;
                }
            }
        } else {
block_70:
            e->target_anim = 0;
            e->ai[1] = var_v0_2;
        }
        break;
    case 5:
    case 6:
    case 7:
        if ((e->force_adjusted != 0) && (e->x_collision == g_ent)) {
            e->target_anim = 1;
            e->ai[1] = 0x8C;
        } else {
            var_s1_3 = 1;
            if (e->anim_done != 0) {
            case 1:
                temp_v0_11 = (u16) e->ai[1];
                var_v0_3 = temp_v0_11 - 1;
                if (temp_v0_11 != 0) {
                    goto block_62;
                }
                if ((g_ent->tile_y - e->tile_y) >= 0xF) {
                    var_v0_5 = 7;
                } else {
                    temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                    var_v0_5 = *(&D_80027CE0 + (((temp_lo_6 + 0xE06A02E7) / MULHI_5) * 2));
                    g_rng_seed = temp_lo_6 + 0xE06A02E7;
                }
                e->target_anim = (s32) var_v0_5;
                temp_v1_5 = e->target_anim;
                e->cur_anim = -1;
                var_s2_3 = temp_v1_5 - 2;
                if (temp_v1_5 == 1) {
                    goto block_67;
                }
                goto block_68;
            }
        }
        break;
    case 8:
        var_v0_2 = 0x28;
        if (sees_player(e, &sp20, 3, 0xA, 0x100000) != 0) {
            goto block_70;
        }
        break;
    case 9:
        *(s32 *)0x801E6378 |= 2;
        break;
    case 11:
        *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 1);
        /* fallthrough */
    case 10:
        var_s1_3 = 1;
        break;
    }
    if (var_s1_3 != 0) {
        if (e->bytes[2] == 0) {
            temp_lo_7 = g_rng_seed * 0x7D2B89DD;
            temp_v1_6 = temp_lo_7 + 0xE06A02E7;
            temp_lo_8 = temp_v1_6 * 0x7D2B89DD;
            temp_t2 = temp_lo_8 + 0xE06A02E7;
            g_rng_seed = temp_v1_6;
            g_rng_seed = temp_t2;
            sp48 = temp_t2 * 0x15;
            sp4C = (temp_lo_8 + 0xE06A02E7) / MULHI_21;
            spawn_effect(1, 0, 0, e->px + (((temp_lo_7 + 0xE06A02E7) / MULHI_121) << 0x10) + 0xFFC40000, e->py + 0x200000, e->pz + (((temp_lo_8 + 0xE06A02E7) / MULHI_21) << 0x10));
            play_sound(0x2E);
            e->bytes[2] = 8;
        }
        e->bytes[2] -= 1;
    }
}
