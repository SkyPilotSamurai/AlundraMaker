/* 8006E530: built-in program C27 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C27(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 temp_v0_2;
    s16 temp_v0_6;
    s16 temp_v0_7;
    s16 var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_s3;
    s32 temp_v0_4;
    s32 temp_v1;
    s32 var_s1;
    s32 var_s2;
    struct Entity *temp_v0_3;
    u16 temp_v0;
    u16 temp_v0_5;
    u32 temp_a0;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 4:
        if ((sp20 < 3) && (sp24 < 3) && (sp28 <= 0x100000)) {
            e->target_anim = 2;
            return;
        }
    default:
        return;
    case 2:
        if (e->anim_done != 0) {
            e->target_anim = 3;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            var_v0 = 0x15;
block_32:
            e->ai[1] = var_v0;
        }
        break;
    case 3:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0_2;
            if (!(temp_v0_2 & 0xFFFF)) {
                var_s2 = 0;
                temp_s3 = e->pz + 0x200000;
                var_s1 = e->target_dir - 6;
                do {
                    var_s2 += 1;
                    temp_v0_3 = spawn_warp_entity(e, 1, 0xCE, e->px, /* extra? */ e->py, /* extra? */ temp_s3, /* extra? */ var_s1);
                    var_s1 = (var_s1 + 4) & 0x1F;
                    temp_v0_3->fz = 0x40000;
                } while (var_s2 != 4);
            }
        }
        if (e->anim_done != 0) {
            temp_v0_4 = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
            temp_lo = g_rng_seed * 0x7D2B89DD;
            temp_a0 = temp_lo + 0xE06A02E7;
            temp_lo_2 = temp_a0 * 0x7D2B89DD;
            sp38 = temp_a0 * 5;
            sp3C = (temp_lo + 0xE06A02E7) / MULHI_5;
            e->target_anim = 1;
            g_rng_seed = temp_a0;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->target_dir = (temp_v0_4 + (((temp_lo + 0xE06A02E7) / MULHI_5) - 2)) & 0x1F;
            e->bytes[0] = 1;
            var_v0 = ((temp_lo_2 + 0xE06A02E7) / 134217728) + 0x78;
            goto block_32;
        }
        break;
    case 0:
        temp_v0_5 = (u16) e->ai[1];
        temp_v0_6 = temp_v0_5 - 1;
        if ((temp_v0_5 == 0) || (e->ai[1] = temp_v0_6, ((temp_v0_6 & 0xFFFF) == 0))) {
            start_moving_half(e, 1, 0x78);
            return;
        }
        break;
    case 1:
        temp_v0_7 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_7;
        if (!(temp_v0_7 & 0xFFFF)) {
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            e->bytes[0] = 0;
            var_v0 = ((temp_lo_3 + 0xE06A02E7) / 134217728) + 0x78;
            goto block_32;
        }
        if (e->bytes[0] == 1) {
            if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                e->bytes[0] = 0;
                var_v0 = ((temp_lo_4 + 0xE06A02E7) / 134217728) + 0x78;
                goto block_32;
            }
        } else {
            if (sees_player(e, &sp20, 2, 4, 0x100000) != 0) {
                e->target_anim = 3;
                var_v0 = 0x15;
                goto block_32;
            }
            if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                temp_lo_5 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_5 + 0xE06A02E7;
                e->target_dir = (temp_lo_5 + 0xE06A02E7) / 134217728;
                return;
            }
        }
        break;
    case 6:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
                return;
            }
            temp_lo_6 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_6 + 0xE06A02E7;
            var_v0 = ((temp_lo_6 + 0xE06A02E7) / 268435456) + 0x20;
            goto block_32;
        }
        break;
    }
}
