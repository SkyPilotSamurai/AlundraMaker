/* 8007318C: built-in program C41 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C41(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_3;
    s16 temp_v0_5;
    s16 temp_v0_7;
    s16 temp_v0_9;
    s16 var_v1;
    s32 temp_lo;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_v0;
    s32 var_v0_2;
    struct Entity *temp_s1;
    u32 temp_v1_3;
    u8 temp_v0;
    u8 temp_v0_10;
    u8 temp_v0_2;
    u8 temp_v0_4;
    u8 temp_v0_6;
    u8 temp_v0_8;

    temp_s1 = e->parent;
    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1; irregular */
    case 0:                                         /* switch 1 */
        e->target_anim = 1;
        e->bytes[1] = temp_s1->bytes[1];
        temp_s1->bytes[2] = 1;
        temp_v0 = e->bytes[1];
        switch (temp_v0) {                          /* switch 2 */
        case 1:                                     /* switch 2 */
        case 4:                                     /* switch 2 */
            e->bytes[2] = 0x14;
            return;
        case 2:                                     /* switch 2 */
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->bytes[2] = 0xF;
            e->ai[1] = 0xB4;
            return;
        case 3:                                     /* switch 2 */
            e->ai[1] = 0x14;
            e->bytes[0] = 0;
            var_v0 = *(&D_80028AF8 + temp_s1->anim_quadrant) + 8;
block_34:
            e->target_dir = var_v0 & 0x1F;
            return;
        case 5:                                     /* switch 2 */
            e->bytes[2] = 1;
            return;
        case 6:                                     /* switch 2 */
        case 7:                                     /* switch 2 */
            e->bytes[2] = 6;
            return;
        default:                                    /* switch 2 */
        default:                                    /* switch 3 */
        default:                                    /* switch 4 */
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v0_2 = e->bytes[1];
        switch (temp_v0_2) {                        /* switch 3 */
        case 1:                                     /* switch 3 */
        case 4:                                     /* switch 3 */
            if ((u16) e->ai[1] == 0) {
                e->ai[1] = 0xF;
            }
            temp_v0_3 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_3;
            if (!(temp_v0_3 & 0xFFFF)) {
                spawn_warp_entity(e, 1, 0xF2, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0xA00000), /* extra? */ e->target_dir);
                temp_v0_4 = e->bytes[2] - 1;
                e->bytes[2] = temp_v0_4;
                if (temp_v0_4 & 0xFF) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo + 0xE06A02E7;
                    e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
                    return;
                }
            case 18:                                /* switch 4 */
block_44:
                remove_entity(e);
                temp_s1->bytes[2] = 0;
            } else if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
                return;
            }
            break;
        case 2:                                     /* switch 3 */
            temp_v0_5 = (u16) e->ai[1] - 1;
            temp_v1_2 = temp_v0_5 & 0xFFFF;
            e->ai[1] = temp_v0_5;
            if ((temp_v1_2 == 0x78) || (temp_v1_2 == 0x3C)) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            }
            if (((u16) e->ai[1] != 0) && (e->force_adjusted == 0) && (ledge_ahead(e, 0) == 0)) {
                temp_v0_6 = e->bytes[2] - 1;
                e->bytes[2] = temp_v0_6;
                if (!(temp_v0_6 & 0xFF)) {
                    spawn_warp_entity(e, 1, 0xF2, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0xA00000), /* extra? */ e->target_dir);
                    e->bytes[2] = 0xF;
                    return;
                }
            } else {
                goto block_44;
            }
            break;
        case 3:                                     /* switch 3 */
            temp_v0_7 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_7;
            if (!(temp_v0_7 & 0xFFFF)) {
                temp_v0_8 = e->bytes[0];
                e->bytes[0] = temp_v0_8 + 1;
                temp_v1_3 = temp_v0_8 & 0xFF;
                switch (temp_v1_3) {                /* switch 4 */
                case 0:                             /* switch 4 */
                    var_v0_2 = e->target_dir;
                    var_v1 = 5;
block_36:
                    e->ai[1] = var_v1;
                    e->target_dir = (var_v0_2 - 8) & 0x1F;
                    spawn_warp_entity(e, 1, 0xF2, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0xA00000), /* extra? */ e->target_dir);
                    return;
                case 2:                             /* switch 4 */
                case 4:                             /* switch 4 */
                case 6:                             /* switch 4 */
                case 8:                             /* switch 4 */
                case 10:                            /* switch 4 */
                case 12:                            /* switch 4 */
                case 14:                            /* switch 4 */
                case 16:                            /* switch 4 */
                    spawn_warp_entity(e, 1, 0xF2, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0xA00000), /* extra? */ e->target_dir);
                    /* fallthrough */
                case 1:                             /* switch 4 */
                case 3:                             /* switch 4 */
                case 5:                             /* switch 4 */
                case 7:                             /* switch 4 */
                case 9:                             /* switch 4 */
                case 11:                            /* switch 4 */
                case 13:                            /* switch 4 */
                case 15:                            /* switch 4 */
                    e->ai[1] = 5;
                    var_v0 = e->target_dir - 1;
                    goto block_34;
                case 17:                            /* switch 4 */
                    var_v0_2 = e->target_dir;
                    var_v1 = 0x14;
                    goto block_36;
                }
            } else {
block_42:
                if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                    goto block_44;
                }
            }
            break;
        case 5:                                     /* switch 3 */
        case 6:                                     /* switch 3 */
        case 7:                                     /* switch 3 */
            if ((u16) e->ai[1] == 0) {
                e->ai[1] = 0x14;
            }
            temp_v0_9 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_9;
            if (!(temp_v0_9 & 0xFFFF)) {
                spawn_warp_entity(e, 1, 0xF2, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0xA00000), /* extra? */ e->target_dir);
                temp_v0_10 = e->bytes[2] - 1;
                e->bytes[2] = temp_v0_10;
                if (temp_v0_10 & 0xFF) {
                    return;
                }
                goto block_44;
            }
            goto block_42;
        }
        break;
    }
}
