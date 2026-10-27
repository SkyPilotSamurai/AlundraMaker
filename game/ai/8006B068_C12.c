/* 8006B068: built-in program C12 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C12(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 temp_v0_4;
    s16 temp_v0_5;
    s16 temp_v0_7;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_s0;
    s32 temp_v0_10;
    s32 temp_v0_6;
    s32 temp_v0_9;
    s32 temp_v1;
    s32 var_a3;
    s32 var_hi;
    s32 var_v0_3;
    u16 temp_v0;
    u8 temp_v0_8;
    u8 temp_v1_2;
    u8 temp_v1_3;
    u8 temp_v1_4;
    u8 temp_v1_5;
    u8 var_v0;
    u8 var_v0_2;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    if (temp_v1 != 6) {
        if (temp_v1 == 7) {
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    play_sound(0x40);
                    e->target_anim = 2;
                    e->flags |= 0x40;
                    return;
                }
                play_sound(0x7D);
                e->target_anim = 4;
                e->delay = 0;
                if (e->bytes[2] == 0) {
                    var_v0 = 3;
                    goto block_53;
                }
                e->bytes[0] = 4;
                var_v0_2 = 7;
                goto block_104;
            }
        } else {
            if ((((u32) temp_v1 < 2U) || (temp_v1 == 5)) && (g_ent->atk_on != 0) && (g_ent->attack_addr != NULL) && (*g_ent->attack_addr != 0) && (sp18 < 3) && (sp1C < 3)) {
                play_sound(0x7D);
                e->target_anim = 4;
                var_v0 = 3;
                goto block_53;
            }
            temp_v1_2 = e->bytes[0];
            switch (temp_v1_2) {                    /* switch 1; irregular */
            case 0:                                 /* switch 1 */
                temp_v0 = (u16) e->ai[1];
                if (temp_v0 != 0) {
                    e->ai[1] = temp_v0 - 1;
                    return;
                }
                e->bytes[1] = 0;
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                if (((temp_lo + 0xE06A02E7) / 1073741824) != 0) {
                    e->bytes[0] = 3;
                    play_sound(0x7D);
                    e->target_anim = 4;
                    return;
                }
                e->bytes[0] = 1;
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 1;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->ai[1] = 0x78;
                e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
                return;
            case 1:                                 /* switch 1 */
                temp_v1_3 = e->bytes[1];
                switch (temp_v1_3) {                /* switch 2 */
                case 0:                             /* switch 2 */
                    temp_v0_2 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_2;
                    if (!(temp_v0_2 & 0xFFFF)) {
                        e->target_anim = 0;
                        e->bytes[1] = 4;
                        e->ai[1] = 0x3C;
                        var_v0_3 = *(&D_80028AF8 + e->anim_quadrant) + 8;
block_77:
                        e->target_dir = var_v0_3 & 0x1F;
                        return;
                    }
                    if (e->force_adjusted != 0) {
                        temp_s0 = height_ahead(e, 9, e->target_dir) - e->floor;
                        if (temp_s0 <= 0x300000) {
                            play_sound(0x7D);
                            e->target_anim = 4;
                            e->delay = temp_s0;
                            e->bytes[1] = 1;
                            e->item_state = (s32) (u16) e->ai[1];
                            return;
                        }
                        goto block_66;
                    }
                    if (ledge_ahead(e, 0x300000) == 0) {
                        var_a3 = 4;
block_52:
                        var_v0 = 4;
                        if (sees_player(e, &sp18, 2, var_a3, M2C_ERROR(/* Unable to find stack arg 0x10 in block */)) != 0) {
block_53:
                            e->bytes[0] = var_v0;
                            e->bytes[1] = 0;
                            return;
                        }
                    } else {
block_66:
                        e->sfy = 0;
                        e->sfx = 0;
                        e->fy = 0;
                        e->fx = 0;
                        e->tfy = 0;
                        e->tfx = 0;
                        e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
                        return;
                    }
                    break;
                case 1:                             /* switch 2 */
                    if (e->anim_done != 0) {
                        e->ai[1] = 0xF;
                        e->target_anim = 9;
                        e->bytes[1] = 2;
                        e->pz += e->delay;
                        return;
                    }
                    break;
                case 2:                             /* switch 2 */
                    temp_v0_3 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_3;
                    if (!(temp_v0_3 & 0xFFFF)) {
                        play_sound(0x7D);
                        e->target_anim = 5;
                        e->bytes[1] = 3;
                        e->ai[1] = (s16) e->item_state;
                        return;
                    }
                    break;
                case 3:                             /* switch 2 */
                    if (e->anim_done != 0) {
                        e->target_anim = 1;
                        e->bytes[1] = 0;
                        return;
                    }
                    break;
                case 4:                             /* switch 2 */
                case 5:                             /* switch 2 */
                case 6:                             /* switch 2 */
                    temp_v0_4 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_4;
                    if (!(temp_v0_4 & 0xFFFF)) {
                        e->ai[1] = 0x28;
                        if (e->bytes[1] == 4) {
                            e->target_dir = (*(&D_80028AF8 + e->anim_quadrant) + 0x10) & 0x1F;
                        }
                        if (e->bytes[1] == 5) {
                            e->target_dir = (*(&D_80028AF8 + e->anim_quadrant) - 8) & 0x1F;
                        }
                        if (e->bytes[1] == 6) {
                            e->bytes[0] = 0;
                            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                            g_rng_seed = temp_lo_3 + 0xE06A02E7;
                            e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / MULHI_33) + (u16) e->ai[1];
                        }
                        var_v0_2 = e->bytes[1] + 1;
block_104:
                        e->bytes[1] = var_v0_2;
                    } else {
                        var_a3 = 5;
                        goto block_52;
                    }
                    break;
                }
                break;
            case 3:                                 /* switch 1 */
                temp_v1_4 = e->bytes[1];
                switch (temp_v1_4) {                /* switch 3; irregular */
                case 0:                             /* switch 3 */
                    if (e->anim_done != 0) {
                        start_moving(e, 9, 0x50, 0x46);
                        var_v0_2 = 1;
                        goto block_104;
                    }
                    break;
                case 1:                             /* switch 3 */
                    temp_v0_5 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_5;
                    if (!(temp_v0_5 & 0xFFFF)) {
                        play_sound(0x7D);
                        e->target_anim = 5;
                        var_v0_2 = 2;
                        goto block_104;
                    }
                    if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                        goto block_66;
                    }
                    if (sees_player(e, &sp18, 2, 5, 0) != 0) {
                        e->bytes[0] = 4;
                        var_v0_2 = 2;
                        goto block_104;
                    }
                    break;
                case 2:                             /* switch 3 */
                    if (e->anim_done != 0) {
                        temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                        var_hi = (temp_lo_4 + 0xE06A02E7) / 268435456;
                        e->target_anim = 0;
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        e->bytes[0] = 0;
block_101:
                        e->ai[1] = (var_hi >> 0) + 0x1E;
                        return;
                    }
                    break;
                }
                break;
            case 4:                                 /* switch 1 */
                temp_v1_5 = e->bytes[1];
                switch (temp_v1_5) {                /* switch 4 */
                case 0:                             /* switch 4 */
                    play_sound(0x7D);
                    e->target_anim = 4;
                    var_v0_2 = 1;
                    goto block_104;
                case 1:                             /* switch 4 */
                case 2:                             /* switch 4 */
                    if ((e->anim_done != 0) || (e->bytes[1] == 2)) {
                        e->target_anim = 9;
                        temp_v0_6 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                        e->delay = 0;
                        g_rng_seed = temp_lo_5 + 0xE06A02E7;
                        e->ai[1] = 0x50;
                        e->bytes[2] = 3;
                        e->bytes[1] = 3;
                        var_v0_3 = temp_v0_6 + (((temp_lo_5 + 0xE06A02E7) / MULHI_9) - 4);
                        goto block_77;
                    }
                    break;
                case 3:                             /* switch 4 */
                    temp_v0_7 = (u16) e->ai[1] - 1;
                    e->ai[1] = temp_v0_7;
                    if (!(temp_v0_7 & 0xFFFF) || (e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                        temp_v0_8 = e->bytes[2] - 1;
                        e->bytes[2] = temp_v0_8;
                        if (!(temp_v0_8 & 0xFF)) {
                            play_sound(0x7D);
                            e->target_anim = 5;
                            var_v0_2 = 6;
                            goto block_104;
                        }
                        e->target_anim = 9;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->ai[1] = 0x3C;
                        return;
                    }
                    temp_v0_9 = e->delay;
                    temp_v0_10 = temp_v0_9 - 1;
                    if (((temp_v0_9 == 0) || (e->delay = temp_v0_10, (temp_v0_10 == 0))) && (sp18 < 3) && (sp1C < 3) && (sp20 == 0) && ((u16) e->ai[1] < 0x28U)) {
                        play_sound(0x7D);
                        e->target_anim = 5;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        var_v0_2 = 4;
                        goto block_104;
                    }
                    break;
                case 4:                             /* switch 4 */
                    if (e->anim_done != 0) {
                        e->target_anim = 3;
                        var_v0_2 = 5;
                        goto block_104;
                    }
                    break;
                case 5:                             /* switch 4 */
                    if ((e->anim_done != 0) || (e->target_anim == 0)) {
                        var_v0_2 = 6;
                        if (e->bytes[2] == 1) {
                            e->target_anim = 0;
                            goto block_104;
                        }
                        play_sound(0x7D);
                        e->target_anim = 4;
                        e->bytes[1] = 7;
                        e->delay = 0x1E;
                        return;
                    }
                    break;
                case 6:                             /* switch 4 */
                    if ((e->anim_done != 0) || (e->target_anim == 0)) {
                        e->bytes[0] = 0;
                        temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                        var_hi = (temp_lo_6 + 0xE06A02E7) / 268435456;
                        e->target_anim = 0;
                        g_rng_seed = temp_lo_6 + 0xE06A02E7;
                        goto block_101;
                    }
                    break;
                case 7:                             /* switch 4 */
                    if (e->anim_done != 0) {
                        e->target_anim = 9;
                        e->ai[1] = 1;
                        var_v0_2 = 3;
                        goto block_104;
                    }
                    break;
                }
                break;
            }
        }
    } else {
    default:                                        /* switch 2 */
    default:                                        /* switch 4 */
    }
}
