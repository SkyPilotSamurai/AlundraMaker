/* 8006E154: built-in program C26 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_800273FC;
extern ? D_80027400;
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C26(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 temp_v0_5;
    s16 var_v0;
    s32 temp_a3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_4;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if ((temp_v0 == 0) || (e->ai[1] = temp_v0_2, ((temp_v0_2 & 0xFFFF) == 0))) {
            if ((sp20 < 3) && (sp24 < 3)) {
                if (sp28 <= 0x200000) {
                    if (e->bytes[1] == 0) {
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->target_anim = 3;
                        e->bytes[1] = 1;
                        var_v0 = 0x37;
block_32:
                        e->ai[1] = var_v0;
                    } else {
                        goto block_10;
                    }
                } else {
                    goto block_10;
                }
            } else {
block_10:
                temp_lo = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 1;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[1] = ((temp_lo + 0xE06A02E7) / MULHI_61) + 0x3C;
                if ((sp20 < 4) && (sp24 < 4)) {
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                }
block_25:
                e->bytes[1] = 0;
                return;
            }
        } else {
        default:
            return;
        }
        break;
    case 1:
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (!(temp_v0_3 & 0xFFFF)) {
            if (e->force_adjusted != 0) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
                var_v0 = ((temp_lo_2 + 0xE06A02E7) / MULHI_31) + 0x1E;
                goto block_32;
            }
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 524288) & 0x7F;
            e->target_dir = (temp_lo_3 + 0xE06A02E7) / 134217728;
            return;
        }
        break;
    case 2:
        if ((sp20 < 4) && (sp24 < 4)) {
            e->target_anim = 4;
            return;
        }
        break;
    case 3:
        temp_v0_4 = (u16) e->ai[1];
        temp_v0_5 = temp_v0_4 - 1;
        if (temp_v0_4 != 0) {
            e->ai[1] = temp_v0_5;
            if (!(temp_v0_5 & 0xFFFF)) {
                temp_a3 = e->anim_quadrant * 8;
                spawn_warp_entity(e, 1, 0x4A, e->px + *(&D_800273FC + temp_a3), /* extra? */ (e->py + *(&D_80027400 + temp_a3)), /* extra? */ (e->pz + 0xA0000), /* extra? */ (s32) *(&D_80028AF8 + e->anim_quadrant))->fz = 0x20000;
            }
        }
        if (e->anim_done != 0) {
            start_moving(e, 1, 0x28, 0x1E);
            goto block_25;
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 6;
                e->flags |= 0x40;
                return;
            }
            var_v0 = 0x28;
block_31:
            e->target_anim = 0;
            goto block_32;
        }
        break;
    case 4:
        var_v0 = 0x1E;
        if (e->anim_done != 0) {
            goto block_31;
        }
        break;
    }
}
