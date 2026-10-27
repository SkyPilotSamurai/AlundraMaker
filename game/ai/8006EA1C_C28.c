/* 8006EA1C: built-in program C28 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_8002745C;
extern ? D_80027460;

void AI_C28(struct Entity *e) {
    s32 sp20;
    s16 temp_v0;
    s16 temp_v0_3;
    s16 var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_s0;
    s32 temp_s0_2;
    s32 temp_s1;
    s32 temp_s1_2;
    s32 temp_s2;
    s32 temp_v0_4;
    s32 temp_v1;
    struct Entity *temp_v0_5;
    u16 temp_v0_2;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        if (e->on_ground != 0) {
            if ((u16) e->ai[1] == 0) {
                e->ai[1] = 0x3C;
            }
            temp_v0 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0;
            if (!(temp_v0 & 0xFFFF)) {
                if (e->bytes[1] != 0) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    e->target_anim = 1;
                    g_rng_seed = temp_lo + 0xE06A02E7;
                    e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
                } else {
                    temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    e->target_dir = (e->target_dir + ((temp_lo_2 + 0xE06A02E7) / MULHI_31) + 1) & 0x1F;
                    if (e->bytes[0] == 3) {
                        e->target_anim = 9;
                        e->bytes[0] = 0;
                    } else {
                        e->target_anim = 1;
                        e->bytes[1] = 4;
                    }
                }
            }
        }
        break;
    case 1:
        if (e->anim_done != 0) {
            e->bytes[1] -= 1;
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_3 + 0xE06A02E7) / 268435456) + 0x1E;
            if (e->bytes[1] == 0) {
                e->bytes[0] += 1;
            }
        } else if (sees_player(e, &sp20, 2, 3, 0x300000) != 0) {
            e->target_anim = 3;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->bytes[2] = 1;
        } else if (sees_player(e, &sp20, 1, 6, 0x300000) != 0) {
            e->target_anim = 4;
            var_v0 = 0x18;
block_33:
            e->ai[1] = var_v0;
        } else if (e->force_adjusted != 0) {
            step_or_turn(e, 1, 9, 0x300000);
        } else {
            ledge_turn(e, 1, 0x300000);
        }
        break;
    case 4:
        temp_v0_2 = (u16) e->ai[1];
        temp_v0_3 = temp_v0_2 - 1;
        if (temp_v0_2 != 0) {
            e->ai[1] = temp_v0_3;
            if (!(temp_v0_3 & 0xFFFF)) {
                temp_s1 = e->px;
                temp_s0 = e->py;
                temp_s2 = e->pz;
                temp_v0_4 = e->anim_quadrant * 8;
                temp_s1_2 = temp_s1 + *(&D_8002745C + temp_v0_4);
                temp_s0_2 = temp_s0 + *(&D_80027460 + temp_v0_4);
                temp_v0_5 = spawn_warp_entity(e, 1, 0xD4, temp_s1_2, /* extra? */ temp_s0_2, /* extra? */ temp_s2, /* extra? */ ((dir_from_delta(g_ent->px - temp_s1, g_ent->py - temp_s0) + 2) & 0x1C));
                if (temp_v0_5 != NULL) {
                    temp_v0_5->anim_quadrant = e->anim_quadrant;
                }
            }
        }
        break;
    case 8:
        if (e->on_ground != 0) {
            if (e->bytes[2] == 0) {
                var_v0 = 0x28;
                e->target_anim = 0;
                goto block_33;
            }
            e->target_anim = 9;
            e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
            e->bytes[2] = 0;
        }
        break;
    case 6:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
            } else {
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 0;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                e->bytes[2] = 0;
                var_v0 = ((temp_lo_4 + 0xE06A02E7) / 268435456) + 0x20;
                goto block_33;
            }
        }
        break;
    }
    e->target_dir = (e->target_dir + 2) & 0x1C;
}
