/* 800707AC: built-in program C35 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_800275E0;
extern ? D_800275E4;
extern ? D_80028AF8;

void AI_C35(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 temp_a0;
    s16 temp_v0_5;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_v0_3;
    u16 temp_v0_2;
    u16 temp_v0_4;
    u32 temp_v1_3;
    u32 var_v0_2;
    u8 temp_v0;
    u8 temp_v0_3;
    u8 var_v0;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        if (e->on_ground != 0) {
            temp_v0 = e->bytes[2];
            if (temp_v0 != 0) {
                e->bytes[2] = temp_v0 - 1;
            } else {
                temp_v0_2 = (u16) e->ai[1];
                if (temp_v0_2 != 0) {
                    e->ai[1] = temp_v0_2 - 1;
                }
                if ((e->bytes[1] == 2) || (sees_player(e, &sp20, 1, 6, 0x200000) != 0)) {
                    e->bytes[1] = 0;
                    if ((sp20 < 3) && (sp24 < 3)) {
                        e->target_anim = 9;
                        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                        e->ai[1] = 0x3C;
                        var_v0 = 1;
block_55:
                        e->bytes[1] = var_v0;
                    } else {
                        var_v0_2 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
block_41:
                        g_rng_seed = var_v0_2;
                        if ((var_v0_2 / MULHI_5) == 0) {
                            play_sound(0xCD);
                        }
                        e->target_anim = 5;
block_44:
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->ai[1] = 0x12;
                    }
                } else if ((u16) e->ai[1] == 0) {
                    temp_v0_3 = e->bytes[0];
                    e->bytes[0] = temp_v0_3 + 1;
                    temp_v1_2 = temp_v0_3 & 0xFF;
                    if (temp_v1_2 != 1) {
                        if (temp_v1_2 < 2) {
                            if (temp_v1_2 != 0) {
                                e->bytes[0] = 0;
                            } else {
                                e->ai[1] = 0x3C;
                                var_v0_3 = *(&D_80028AF8 + e->anim_quadrant) + 8;
                                goto block_27;
                            }
                        } else if (temp_v1_2 != 2) {
                            e->bytes[0] = 0;
                        } else {
                            temp_lo = g_rng_seed * 0x7D2B89DD;
                            temp_v1_3 = temp_lo + 0xE06A02E7;
                            temp_lo_2 = temp_v1_3 * 0x7D2B89DD;
                            sp38 = temp_v1_3 * 0x20;
                            sp3C = (temp_lo + 0xE06A02E7) / 134217728;
                            e->target_anim = 9;
                            g_rng_seed = temp_v1_3;
                            g_rng_seed = temp_lo_2 + 0xE06A02E7;
                            e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
                            e->bytes[1] = 0;
                            e->ai[1] = ((temp_lo_2 + 0xE06A02E7) / 268435456) + 0x3C;
                        }
                    } else {
                        e->ai[1] = 0x3C;
                        var_v0_3 = *(&D_80028AF8 + e->anim_quadrant) + 0x10;
block_27:
                        e->target_dir = var_v0_3 & 0x1F;
                    }
                }
            }
        }
        break;
    case 9:
        temp_a0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_a0;
        if ((e->bytes[1] == 1) && (!(temp_a0 & 0xFFFF) || (e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0))) {
            e->target_anim = 5;
            goto block_44;
        }
        if ((u16) e->ai[1] == 0) {
            e->target_anim = 0;
            e->ai[1] = 0x3C;
        } else {
            if (sees_player(e, &sp20, 1, 6, 0x200000) != 0) {
                if ((sp20 < 3) && (sp24 < 3)) {
                    e->target_anim = 9;
                    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                    e->ai[1] = 0x3C;
                    var_v0 = 1;
                    goto block_55;
                }
                var_v0_2 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                goto block_41;
            }
            if (e->force_adjusted != 0) {
                step_or_turn(e, 9, 3, 0x300000);
            } else {
                ledge_turn(e, 9, 0x300000);
            }
        }
        break;
    case 5:
        temp_v0_4 = (u16) e->ai[1];
        temp_v0_5 = temp_v0_4 - 1;
        if (temp_v0_4 != 0) {
            e->ai[1] = temp_v0_5;
            if (!(temp_v0_5 & 0xFFFF)) {
                temp_a3 = e->anim_quadrant * 8;
                spawn_warp_entity(e, 1, 0x65, e->px + *(&D_800275E0 + temp_a3), /* extra? */ (e->py + *(&D_800275E4 + temp_a3)), /* extra? */ (e->pz + 0xA0000), /* extra? */ ((e->target_dir - 7) & 0x1F));
                e->bytes[2] = 0x1E;
            }
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
            } else {
                var_v0 = 2;
                e->target_anim = 0;
                e->bytes[2] = 0;
                e->bytes[0] = 0;
                goto block_55;
            }
        }
        break;
    }
    if ((e->target_anim == 3) || (e->target_anim == 5)) {
        e->target_dir = (e->target_dir + 2) & 0x1C;
    }
}
