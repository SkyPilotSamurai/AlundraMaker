/* 8007033C: built-in program C33 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_800275C0;
extern ? D_800275C4;
extern ? D_80028AF8;

void AI_C33(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 var_v0_2;
    s32 temp_a2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 var_v0;
    struct Entity *temp_v0_5;
    u16 temp_v0;
    u16 temp_v0_3;
    u8 temp_v1_2;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1; irregular */
    case 0:                                         /* switch 1 */
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        e->target_anim = 6;
        e->target_dir = (s32) *(&D_80028AF8 + e->anim_quadrant);
        return;
    case 6:                                         /* switch 1 */
        temp_v1_2 = e->bytes[0];
        switch (temp_v1_2) {                        /* switch 2; irregular */
        case 0:                                     /* switch 2 */
            if ((sp20 < 7) && (sp24 < 7) && (sp28 <= 0x200000)) {
                if ((sp20 < 3) && (sp24 < 3)) {
                    e->bytes[0] = 1;
                    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                    e->ai[1] = 0x1E;
                    return;
                }
                e->target_anim = 2;
block_43:
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x21;
                return;
            }
            if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                e->bytes[2] += 1;
                temp_lo = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 0;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[1] = ((temp_lo + 0xE06A02E7) / 134217728) + 0x3C;
                if ((u8) e->bytes[2] >= 3U) {
                    e->bytes[2] = 0;
                    if ((u16) e->ai[1] & 1) {
                        var_v0 = *(&D_80028AF8 + e->anim_quadrant) + 8;
                    } else {
                        var_v0 = *(&D_80028AF8 + e->anim_quadrant) - 8;
                    }
                } else {
                    var_v0 = *(&D_80028AF8 + e->anim_quadrant) - 0x10;
                }
                e->target_dir = var_v0 & 0x1F;
                return;
            }
            return;
        case 1:                                     /* switch 2 */
            temp_v0_2 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_2;
            if (!(temp_v0_2 & 0xFFFF) || (e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                if (((temp_lo_2 + 0xE06A02E7) / MULHI_5) == 0) {
                    play_sound(0xCD);
                }
                e->target_anim = 2;
                goto block_43;
            }
            break;
        }
        break;
    case 2:                                         /* switch 1 */
        temp_v0_3 = (u16) e->ai[1];
        temp_v0_4 = temp_v0_3 - 1;
        if (temp_v0_3 != 0) {
            e->ai[1] = temp_v0_4;
            if (!(temp_v0_4 & 0xFFFF)) {
                temp_a2 = e->anim_quadrant * 8;
                temp_v0_5 = spawn_warp_entity(e, 1, 0x5F, e->px + *(&D_800275C0 + temp_a2), /* extra? */ (e->py + *(&D_800275C4 + temp_a2)), /* extra? */ (e->pz + 0x100000), /* extra? */ e->target_dir);
                if (temp_v0_5 != NULL) {
                    temp_v0_5->anim_quadrant = e->anim_quadrant;
                }
            }
        }
        if (e->anim_done != 0) {
            var_v0_2 = 0xA;
            if (sp20 < 7) {
                if (sp24 < 7) {
                    var_v0_2 = 0xA;
                    if (sp28 <= 0x200000) {
                        e->cur_anim = -1;
                        goto block_43;
                    }
                    goto block_45;
                }
                var_v0_2 = 0xA;
                goto block_45;
            }
block_45:
            e->target_anim = 0;
block_50:
            e->ai[1] = var_v0_2;
            e->bytes[0] = 0;
        }
        break;
    case 4:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 5;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 2;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            var_v0_2 = 0x21;
            goto block_50;
        }
        break;
    }
}
