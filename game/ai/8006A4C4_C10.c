/* 8006A4C4: built-in program C10 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C10(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_4;
    s16 var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_3;
    u32 temp_a0;
    u32 temp_a0_2;
    u32 temp_a0_3;
    u32 temp_v1_2;
    u8 temp_v0_2;
    u8 var_v1;

    if ((g_cur_map == 0x99) && (e->parent->bytes[3] != 0)) {
        destroy_entity(e, -1);
        return;
    }
    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 0:                                         /* switch 1 */
        if (e->bytes[0] == 0) {
            if (sees_player(e, &sp18, 2, 6, 0x100000) != 0) {
                e->bytes[0] = 1;
                e->ai[1] = 0;
            } else {
                temp_v0 = (u16) e->ai[1];
                var_v0 = temp_v0 - 1;
                if (temp_v0 == 0) {
                    if ((e->bytes[1] != 0) || (temp_lo = g_rng_seed * 0x7D2B89DD, g_rng_seed = temp_lo + 0xE06A02E7, (((temp_lo + 0xE06A02E7) / 1073741824) == 1))) {
                        temp_v0_2 = e->bytes[1];
                        e->bytes[1] = temp_v0_2 + 1;
                        temp_v1_2 = temp_v0_2 & 0xFF;
                        switch (temp_v1_2) {        /* switch 2 */
                        case 0:                     /* switch 2 */
                        case 1:                     /* switch 2 */
                        case 2:                     /* switch 2 */
                            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                            g_rng_seed = temp_lo_2 + 0xE06A02E7;
                            if (((temp_lo_2 + 0xE06A02E7) / 1073741824) == 0) {
                                play_sound(0xCD);
                            }
                            e->target_anim = 8;
                            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                            break;
                        case 3:                     /* switch 2 */
                            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                            e->sfy = 0;
                            e->sfx = 0;
                            e->fy = 0;
                            e->fx = 0;
                            e->tfy = 0;
                            e->tfx = 0;
                            g_rng_seed = temp_lo_3 + 0xE06A02E7;
                            var_v1 = *(&D_80028AF8 + ((temp_lo_3 + 0xE06A02E7) / 1073741824));
block_18:
                            e->ai[1] = 0x14;
                            e->target_dir = (s32) var_v1;
                            break;
                        case 4:                     /* switch 2 */
                            e->sfy = 0;
                            e->sfx = 0;
                            e->fy = 0;
                            e->fx = 0;
                            e->tfy = 0;
                            e->tfx = 0;
                            var_v1 = *(&D_80028AD8 + e->target_dir);
                            goto block_18;
                        case 5:                     /* switch 2 */
                            e->target_anim = 0xC;
                            var_v0 = 0x78;
                            goto block_75;
                        default:                    /* switch 2 */
                            e->bytes[1] = 0;
                            e->ai[1] = 0;
                            break;
                        }
                    }
                } else {
                    goto block_75;
                }
            }
        } else if ((sees_player(e, &sp18, 2, 6, 0x100000) != 0) || (var_v0 = 0x1E, (sees_player_q(e, &sp18, e->unk98 ^ 1, 2, 3, 0x100000) != 0))) {
            temp_v0_3 = (u16) e->ai[1];
            var_v0 = temp_v0_3 - 1;
            if (temp_v0_3 == 0) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                if ((g_ent->atk_on != 0) && (g_ent->attack_addr != NULL) && (*g_ent->attack_addr != 0) && (sp18 < 5) && (sp1C < 5)) {
                    temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_4 + 0xE06A02E7;
                    if (((temp_lo_4 + 0xE06A02E7) / 1073741824) == 0) {
                        play_sound(0xCD);
                    }
                    e->target_anim = 3;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
block_72:
                    e->ai[1] = 0x1E;
                    e->bytes[1] = 0;
                } else if ((sp18 < 3) && (sp1C < 3)) {
                    temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_5 + 0xE06A02E7;
                    temp_a0 = (temp_lo_5 + 0xE06A02E7) / 536870912;
                    switch (temp_a0) {              /* switch 3 */
                    case 0:                         /* switch 3 */
                        e->target_anim = 0xC;
                        var_v0 = 0x14;
                        goto block_75;
                    case 1:                         /* switch 3 */
                        e->target_anim = 0xC;
                        e->ai[1] = 0x3C;
block_43:
                        e->target_dir = (e->target_dir - 0x10) & 0x1F;
                        break;
                    case 2:                         /* switch 3 */
                    case 3:                         /* switch 3 */
                        e->target_anim = 0xC;
                        e->ai[1] = 0x64;
                        goto block_43;
                    case 4:                         /* switch 3 */
                    case 5:                         /* switch 3 */
                        temp_lo_6 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_6 + 0xE06A02E7;
                        if (((temp_lo_6 + 0xE06A02E7) / 1073741824) == 0) {
                            play_sound(0xCD);
                        }
                        e->target_anim = 7;
                        break;
                    case 6:                         /* switch 3 */
                    case 7:                         /* switch 3 */
                        e->target_anim = 4;
                        goto block_43;
                    }
                } else if ((sp18 < 5) && (sp1C < 5)) {
                    temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_7 + 0xE06A02E7;
                    temp_a0_2 = (temp_lo_7 + 0xE06A02E7) / MULHI_5;
                    switch (temp_a0_2) {            /* switch 4 */
                    case 2:                         /* switch 4 */
                    case 3:                         /* switch 4 */
                        e->ai[1] = 0x14;
                        /* fallthrough */
                    case 4:                         /* switch 4 */
                        e->target_anim = 0xC;
                        var_v0 = 0x1E;
                        goto block_75;
                    }
                } else if ((sp18 < 7) && (sp1C < 7)) {
                    temp_lo_8 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_8 + 0xE06A02E7;
                    temp_a0_3 = (temp_lo_8 + 0xE06A02E7) / 536870912;
                    switch (temp_a0_3) {            /* switch 5 */
                    case 0:                         /* switch 5 */
                    case 1:                         /* switch 5 */
                    case 2:                         /* switch 5 */
                        e->target_anim = 0xC;
                        var_v0 = 0x3C;
                        goto block_75;
                    case 3:                         /* switch 5 */
                        e->target_anim = 0xC;
                        var_v0 = 0x1E;
                        goto block_75;
                    case 4:                         /* switch 5 */
                    case 5:                         /* switch 5 */
                        e->target_anim = 4;
                        break;
                    case 6:                         /* switch 5 */
                    case 7:                         /* switch 5 */
                    case 0:                         /* switch 4 */
                    case 1:                         /* switch 4 */
                        e->target_anim = 8;
                        break;
                    }
                }
            } else {
                goto block_75;
            }
        } else {
            e->bytes[1] = 0;
            e->bytes[0] = 0;
block_75:
            e->ai[1] = var_v0;
        }
        break;
    case 12:                                        /* switch 1 */
        if ((e->bytes[0] != 0) || (sees_player(e, &sp18, 2, 6, 0x100000) == 0)) {
            temp_v0_4 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_4;
            if (!(temp_v0_4 & 0xFFFF) || (e->force_adjusted != 0)) {
                e->target_anim = 0;
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                goto block_72;
            }
            if (ledge_turn(e, 0xC, 0x400000) != 0) {
                goto block_71;
            }
        } else {
block_70:
            e->bytes[0] = 1;
block_71:
            e->target_anim = 0;
            goto block_72;
        }
        break;
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 6;
                e->flags |= 0x40;
            } else {
                goto block_70;
            }
        }
        break;
    case 9:                                         /* switch 1 */
    case 10:                                        /* switch 1 */
        var_v0 = 0x14;
        if (e->on_ground != 0) {
            e->target_anim = 0;
            goto block_75;
        }
        break;
    }
    e->target_dir = (e->target_dir + 2) & 0x1C;
}
