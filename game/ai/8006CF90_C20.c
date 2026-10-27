/* 8006CF90: built-in program C20 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C20(struct Entity *e) {
    s32 sp10;
    s16 temp_v0;
    s16 temp_v0_6;
    s16 temp_v0_7;
    s16 var_v0;
    s16 var_v0_5;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v0_5;
    s32 temp_v1;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_4;
    u16 temp_v0_4;
    u8 temp_v1_2;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 9:                                         /* switch 1 */
        if ((sp10 < 0x1F) && (sp14 < 0x1F)) {
            e->target_anim = 0xA;
block_50:
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            return;
        }
    default:                                        /* switch 1 */
        return;
    case 10:                                        /* switch 1 */
        if (e->bytes[0] == 3) {
            temp_v0 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0;
            if (!(temp_v0 & 0xFFFF)) {
                e->bytes[0] = 0;
                return;
            }
        } else if ((sp10 != 0) || (sp14 != 0) || (var_v0 = 0x78, (sp18 != 0))) {
            temp_v0_2 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->target_dir = temp_v0_2;
            if (e->force_adjusted != 0) {
                temp_v0_3 = height_ahead(e, 0xA, temp_v0_2);
                if (temp_v0_3 != 0x07800000) {
                    temp_a0 = temp_v0_3 - e->floor;
                    e->terrain += temp_a0;
                    e->floor += temp_a0;
                    e->pz += temp_a0;
                    return;
                }
            }
        } else {
block_67:
            e->target_anim = 0;
            e->ai[1] = var_v0;
            return;
        }
        break;
    case 0:                                         /* switch 1 */
        var_v0_2 = 0xA;
        if (e->bytes[0] != 3) {
            temp_v0_4 = (u16) e->ai[1];
            if (temp_v0_4 != 0) {
                e->ai[1] = temp_v0_4 - 1;
                return;
            }
            if ((sp10 < 4) && (sp14 < 4) && (sp18 <= 0)) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                temp_v0_5 = (temp_lo + 0xE06A02E7) / 1073741824;
                switch (temp_v0_5) {                /* switch 2; irregular */
                case 0:                             /* switch 2 */
                    e->target_anim = 3;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->bytes[0] = 1;
                    return;
                case 1:                             /* switch 2 */
                    e->target_anim = 1;
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
block_32:
                    e->ai[1] = 0x28;
                    return;
                case 2:                             /* switch 2 */
                    e->target_anim = 1;
                    var_v0_3 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py) + 4;
block_31:
                    e->target_dir = var_v0_3 & 0x1F;
                    goto block_32;
                case 3:                             /* switch 2 */
                    e->target_anim = 1;
                    var_v0_3 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py) - 4;
                    goto block_31;
                }
            } else {
                var_v0_4 = 9;
                if ((sp10 < 5) && (var_v0_4 = 9, ((sp14 < 5) != 0)) && (var_v0_4 = 9, (sp18 <= 0))) {
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    temp_a0_2 = (temp_lo_2 + 0xE06A02E7) / 2147483648;
                    switch (temp_a0_2) {            /* switch 3; irregular */
                    case 0:                         /* switch 3 */
                        e->target_anim = 1;
                        temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        g_rng_seed = temp_lo_3 + 0xE06A02E7;
                        e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 268435456) + 0x14;
                        return;
                    case 1:                         /* switch 3 */
                        e->target_anim = 3;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->bytes[0] = 2;
                        return;
                    }
                } else {
block_61:
                    e->target_anim = var_v0_4;
                    e->ai[1] = 0;
                    return;
                }
            }
        } else {
block_65:
            e->target_anim = var_v0_2;
            e->ai[1] = 0x3C;
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v0_6 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_6;
        if (!(temp_v0_6 & 0xFFFF)) {
            e->target_anim = 0;
            return;
        }
        var_v0_4 = 9;
        if ((sp10 < 5) && (var_v0_4 = 9, ((sp14 < 5) != 0))) {
            if (((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) && (height_ahead(e, 0xA, e->target_dir) != 0x07800000)) {
                if (sp18 == 0) {
                    e->target_anim = 0;
                    goto block_50;
                }
                e->target_anim = 3;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->bytes[0] = 3;
                return;
            }
        } else {
            goto block_61;
        }
        break;
    case 3:                                         /* switch 1 */
        if (e->anim_done != 0) {
            temp_v1_2 = e->bytes[0];
            switch (temp_v1_2) {                    /* switch 4; irregular */
            default:                                /* switch 4 */
                var_v0_4 = 5;
                if (temp_v1_2 != 3) {
                    return;
                }
                goto block_61;
            case 1:                                 /* switch 4 */
                e->target_anim = 4;
block_73:
                e->bytes[0] = 0;
                break;
            case 2:                                 /* switch 4 */
                e->target_anim = (s32) temp_v1_2;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                var_v0_5 = 0xA;
block_72:
                e->ai[1] = var_v0_5;
                goto block_73;
            }
        }
        break;
    case 2:                                         /* switch 1 */
        temp_v0_7 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_7;
        if (!(temp_v0_7 & 0xFFFF)) {
            e->target_anim = 5;
            return;
        }
        break;
    case 4:                                         /* switch 1 */
        var_v0_2 = 5;
        if (e->anim_done != 0) {
            goto block_65;
        }
        break;
    case 5:                                         /* switch 1 */
        var_v0 = 0x1E;
        if (e->anim_done != 0) {
            goto block_67;
        }
        break;
    case 7:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            var_v0_5 = 0x14;
            e->target_anim = 0;
            goto block_72;
        }
        break;
    }
}
