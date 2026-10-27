/* 800688F8: built-in program C3 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;

void AI_C3(struct Entity *e) {
    s32 sp10;
    s16 temp_v0;
    s16 temp_v0_4;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_v0_3;
    s32 temp_v1;
    u16 temp_v0_2;
    u8 temp_v1_2;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 4:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 5;
        }
        if ((sp10 < 3) && (sp14 < 3) && (sp18 <= 0x100000)) {
            e->target_anim = 5;
            e->bytes[1] = 3;
            return;
        }
    default:
        return;
    case 5:
        if (e->anim_done != 0) {
            temp_v1_2 = e->bytes[1];
            if (temp_v1_2 == 3) {
                e->target_anim = (s32) temp_v1_2;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x78;
                e->bytes[2] = 0;
                e->bytes[1] = 0;
                return;
            }
            start_moving(e, 1, 0x78, 0x14);
            return;
        }
        break;
    case 0:
    case 1:
        temp_v0_2 = (u16) e->ai[1];
        if (temp_v0_2 != 0) {
            e->ai[1] = temp_v0_2 - 1;
        }
        temp_v0_3 = e->delay;
        if (temp_v0_3 != 0) {
            e->delay = temp_v0_3 - 1;
        }
        if ((u16) e->ai[1] == 0) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 6;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / MULHI_31) + 0xB4;
        }
        if ((e->delay != 0) || (sp10 >= 3) || (sp14 >= 3) || (sp18 > 0x100000)) {
            if (e->force_adjusted != 0) {
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
                return;
            }
            ledge_turn(e, 1, 0);
            return;
        }
block_37:
        e->target_anim = 3;
        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        e->ai[1] = 0x78;
        e->bytes[2] = 0;
        break;
    case 3:
        if (g_ent->touching == e) {
            e->bytes[2] = 1;
        }
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF)) {
            if (e->bytes[2] != 0) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                e->delay = 0;
                e->target_anim = 6;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->ai[1] = ((temp_lo_2 + 0xE06A02E7) / MULHI_31) + 0xB4;
                return;
            }
            temp_lo_3 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 1;
            g_rng_seed = temp_lo_3 + 0xE06A02E7;
            if (((temp_lo_3 + 0xE06A02E7) / MULHI_3) == 0) {
                e->target_dir = (e->target_dir + 0x10) & 0x1F;
            }
            e->ai[1] = 0x3C;
            e->delay = 0x3C;
            return;
        }
        break;
    case 8:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            goto block_37;
        }
        break;
    }
}
