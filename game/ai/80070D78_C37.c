/* 80070D78: built-in program C37 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;

void AI_C37(struct Entity *e) {
    s32 sp18;
    s16 temp_v0;
    s32 temp_a0;
    s32 temp_lo;
    s32 temp_v1;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        temp_lo = g_rng_seed * 0x7D2B89DD;
        g_rng_seed = temp_lo + 0xE06A02E7;
        temp_a0 = (temp_lo + 0xE06A02E7) / MULHI_3;
        if (temp_a0 >= 0) {
            if (temp_a0 >= 2) {
                if (temp_a0 == 2) {
                    e->bytes[0] += 1;
                    goto block_11;
                }
            } else {
block_11:
                e->bytes[0] += 1;
            }
        }
        e->target_anim = 2;
        e->bytes[2] = e->bytes[0];
        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        e->ai[1] = 0;
        return;
    case 2:
        if (e->anim_done != 0) {
            if (e->bytes[2] != 0) {
                e->cur_anim = 0;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->bytes[2] -= 1;
                return;
            }
            e->target_anim = 1;
            if ((u16) e->ai[1] == 0) {
                e->ai[1] = 0x19;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->bytes[0] -= 1;
                return;
            }
        } else {
            return;
        }
        break;
    case 1:
        if (e->bytes[1] == 0) {
            spawn_effect(0, 7, 0, e->px, e->py, e->pz);
            e->bytes[1] = 0xA;
        }
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        e->bytes[1] -= 1;
        if (!(temp_v0 & 0xFFFF)) {
            if (e->bytes[0] != 0) {
                e->target_anim = 2;
            } else {
                e->target_anim = 0;
            }
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            return;
        }
        if (e->force_adjusted != 0) {
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            e->target_anim = 2;
            e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
            return;
        }
        break;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 6;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 0;
            e->damaged_tick = 0x5A;
            e->bytes[1] = 0;
            e->bytes[0] = 0;
        }
        break;
    }
}
