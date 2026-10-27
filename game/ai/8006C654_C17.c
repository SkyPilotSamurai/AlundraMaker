/* 8006C654: built-in program C17 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C17(struct Entity *e) {
    s32 sp10;
    s16 temp_v0;
    s16 temp_v0_2;
    s16 var_v0;
    s16 var_v0_3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 var_v0_2;
    s32 var_v0_4;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        if ((u16) e->ai[1] == 0) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = 0x3C;
            e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
        }
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 1;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            var_v0 = ((temp_lo_2 + 0xE06A02E7) / 134217728) + 0x78;
block_34:
            e->ai[1] = var_v0;
        }
    default:
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            e->target_anim = 0;
            return;
        }
        if ((sp20 <= 0) && (sp10 < 4) && (sp18 <= 0x100000)) {
            if ((sp10 != 0) || (var_v0_2 = 4, ((sp20 < -4) != 0))) {
                if (sp20 >= -1) {
                    var_v0_2 = 2;
                    if (sp1C >= -1) {
                        e->target_anim = 2;
                        goto block_19;
                    }
                    goto block_20;
                }
                if (sp20 >= -4) {
                    var_v0_2 = 3;
                    if (sp1C >= -1) {
                        goto block_18;
                    }
block_20:
                    e->target_anim = var_v0_2;
                    e->target_dir = 0x18;
                    return;
                }
                goto block_21;
            }
block_18:
            e->target_anim = var_v0_2;
block_19:
            e->target_dir = 0;
            return;
        }
block_21:
        if (e->force_adjusted != 0) {
            e->target_dir = (e->target_dir - 0x10) & 0x1F;
            if (e->anim_quadrant == 0) {
                var_v0_3 = 0xF0;
            } else {
                var_v0_3 = 0x78;
            }
            e->ai[1] = var_v0_3;
            e->target_anim = 1;
            return;
        }
        var_v0_4 = ledge_ahead(e, 0);
block_28:
        if (var_v0_4 != 0) {
            e->target_anim = 0;
            e->ai[1] = 0;
            return;
        }
        break;
    case 2:
    case 3:
    case 4:
        var_v0_4 = e->anim_done;
        goto block_28;
    case 6:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 1;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            var_v0 = 0x78;
            goto block_34;
        }
        break;
    }
}
