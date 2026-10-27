/* 8006FE54: built-in program C32, C34 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80027550;
extern ? D_80027554;
extern ? D_80027570;
extern ? D_80027574;

void AI_C32(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 var_v1;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_t1;
    s32 temp_v0_5;
    s32 temp_v0_6;
    s32 temp_v1;
    s32 var_v1_2;
    struct Entity *temp_v0_7;
    u16 temp_v0;
    u16 temp_v0_3;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        temp_lo = g_rng_seed * 0x7D2B89DD;
        e->target_anim = 1;
        g_rng_seed = temp_lo + 0xE06A02E7;
        e->ai[1] = ((temp_lo + 0xE06A02E7) / 134217728) + 0x78;
        if (((sp20 >= 0xF) && (sp24 >= 0xF)) || (sp28 > 0x6FFFFF)) {
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
            return;
        }
        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        e->ai[1] = (u16) e->ai[1] + 0x28;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 268435456) + 0x3C;
            return;
        }
        if ((sees_player(e, &sp20, 1, 4, 0x100000) == 0) && ((sp20 >= 3) || (sp24 >= 3) || (sp28 > 0x10000))) {
            if (e->force_adjusted != 0) {
                step_or_turn(e, 1, 4, 0x200000);
                return;
            }
            ledge_turn(e, 1, 0x200000);
            return;
        }
block_38:
        e->target_anim = 2;
        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
        return;
    case 5:
        if (e->on_ground != 0) {
            e->target_anim = 3;
            var_v1 = 0xF;
block_34:
            e->ai[1] = var_v1;
            e->target_dir = (e->target_dir + 0x10) & 0x1F;
            return;
        }
    default:
        return;
    case 6:
        if (e->on_ground != 0) {
            e->target_anim = 1;
            return;
        }
        break;
    case 3:
        temp_v0_3 = (u16) e->ai[1];
        temp_v0_4 = temp_v0_3 - 1;
        if (temp_v0_3 != 0) {
            e->ai[1] = temp_v0_4;
            if (!(temp_v0_4 & 0xFFFF)) {
                temp_t1 = e->pz + 0xA0000;
                if (M2C_ERROR(/* Read from unset register $a1 */) == 0x20) {
                    temp_v0_5 = e->anim_quadrant * 8;
                    spawn_warp_entity(e, 1, 0x6E, e->px + *(&D_80027550 + temp_v0_5), /* extra? */ (e->py + *(&D_80027554 + temp_v0_5)), /* extra? */ temp_t1, /* extra? */ e->target_dir);
                } else {
                    temp_v0_6 = e->anim_quadrant * 8;
                    temp_v0_7 = spawn_warp_entity(e, 1, 0x74, e->px + *(&D_80027570 + temp_v0_6), /* extra? */ (e->py + *(&D_80027574 + temp_v0_6)), /* extra? */ temp_t1, /* extra? */ e->target_dir);
                    if (temp_v0_7 != NULL) {
                        temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_4 + 0xE06A02E7;
                        var_v1_2 = (temp_lo_4 + 0xE06A02E7) / MULHI_3;
                        if (var_v1_2 != 0) {
                            var_v1_2 += 1;
                        }
                        temp_v0_7->target_anim = var_v1_2;
                        temp_v0_7->fz = 0x38000;
                    }
                }
            }
        }
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x78;
            return;
        }
        break;
    case 10:
        var_v1 = 0x1E;
        if (e->anim_done != 0) {
            e->target_anim = 0;
            goto block_34;
        }
        break;
    case 9:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            goto block_38;
        }
        break;
    case 11:
        if ((e->target_anim == e->cur_anim) && (e->on_ground != 0)) {
            e->target_anim = 0xA;
        }
        break;
    }
}
