/* 8006928C: built-in program C6 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C6(struct Entity *e) {
    s32 sp10;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_v1;
    u16 temp_v0;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 == 0) {
            e->target_anim = 1;
            e->ai[1] = 1;
            return;
        }
        e->ai[1] = temp_v0 - 1;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            start_moving_half(e, 1, 0xF0);
            return;
        }
        if (e->force_adjusted != 0) {
            step_or_turn(e, 1, 2, 0x100000);
            if (e->target_anim == 1) {
                e->target_anim = 0;
            }
            e->ai[1] = 0x3C;
            return;
        }
    default:
        return;
    case 4:
        if (near_in_front(e, &sp10, 4, 0x100000) != 0) {
            e->target_anim = 3;
            return;
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            e->target_anim = 1;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x12C;
            return;
        }
        break;
    case 6:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
                return;
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            if (((temp_lo + 0xE06A02E7) / 1073741824) == 0) {
                SpawnEntityContents(e);
            }
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 2:
        if (e->on_ground != 0) {
            e->target_anim = 1;
        }
        break;
    }
}
