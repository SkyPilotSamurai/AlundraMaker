/* 8006C924: built-in program C18 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C18(struct Entity *e) {
    s32 sp18;
    s32 sp30;
    s32 sp34;
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 temp_v0_4;
    s16 temp_v0_5;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_t0;
    s32 temp_v1;
    u16 temp_v0;
    u32 temp_t1;
    u32 temp_v1_2;

    rel_tile_z(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        if (e->bytes[0] != 0) {
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x3C;
            e->bytes[0] -= 1;
            if (sp2C > 0xFFFFF) {
                if (sp2C <= 0x180000) {
                    goto block_21;
                }
                goto block_20;
            }
            goto block_16;
        }
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if (temp_v0 == 0) {
            if ((sp18 < 3) && (sp1C < 3) && (sp20 <= 0x200000)) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x3C;
                return;
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            temp_v1_2 = temp_lo + 0xE06A02E7;
            temp_lo_2 = temp_v1_2 * 0x7D2B89DD;
            g_rng_seed = temp_v1_2;
            temp_t1 = temp_lo_2 + 0xE06A02E7;
            g_rng_seed = temp_t1;
            sp30 = temp_v1_2 * 0x20;
            sp34 = (temp_lo + 0xE06A02E7) / 134217728;
            e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
            temp_t0 = e->pz - ((u16) e->ai[0] << 0x10);
            e->ai[1] = ((temp_lo_2 + 0xE06A02E7) / MULHI_41) + 0x50;
            if (temp_t0 <= 0x4FFFFF) {
                temp_lo_3 = temp_t1 * 0x7D2B89DD;
                if (temp_t0 > 0xFFB00000) {
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    e->target_anim = ((temp_lo_3 + 0xE06A02E7) / MULHI_3) + 1;
                    return;
                }
                goto block_16;
            }
            goto block_19;
        }
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            e->ai[1] = 0x78;
            if (sp2C <= 0xFFFFF) {
block_16:
                e->target_anim = 2;
                return;
            }
            if ((sp2C > 0x180000) && (e->on_ground == 0)) {
block_19:
block_20:
                e->target_anim = 3;
                return;
            }
block_21:
            e->target_anim = 1;
            return;
        }
    default:
        return;
    case 1:
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (!(temp_v0_3 & 0xFFFF)) {
            e->target_anim = 0;
        }
        if (e->bytes[0] == 0) {
            if (sees_player(e, &sp18, 1, 4, 0x200000) == 0) {
                if (e->force_adjusted != 0) {
                    e->target_anim = 0;
                    e->target_dir = (e->target_dir + 4) & 0x1F;
                    return;
                }
            } else {
block_35:
                e->target_anim = 0;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0;
                e->bytes[0] = 0xA;
                return;
            }
        }
        break;
    case 2:
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF)) {
            e->target_anim = 0;
        }
block_33:
        if ((e->bytes[0] == 0) && (sees_player(e, &sp18, 1, 4, 0x200000) != 0)) {
            goto block_35;
        }
        break;
    case 3:
        temp_v0_5 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_5;
        if (!(temp_v0_5 & 0xFFFF) || (e->on_ground != 0)) {
            e->target_anim = 0;
        }
        goto block_33;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 6;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 0;
            e->bytes[0] = 0;
            e->ai[1] = 0;
        }
        break;
    }
}
