/* 800685A4: built-in program C2 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C2(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v0_3;
    s32 temp_v1;
    s32 var_v0;
    u16 temp_v0;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 == 0) {
            e->ai[1] = 0x50;
            var_v0 = 1;
block_31:
            e->target_anim = var_v0;
        default:
            return;
        }
        e->ai[1] = temp_v0 - 1;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            start_moving(e, 1, 0x50, 0x1E);
            e->bytes[0] = 0;
            return;
        }
        if ((e->bytes[0] == 0) && (near_in_front(e, &sp18, 2, 0x100000) != 0)) {
            e->target_anim = 0xD;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->unk28C = 0;
            return;
        }
        if (e->force_adjusted != 0) {
            step_or_turn(e, 1, 4, 0x200000);
            return;
        }
        ledge_turn(e, 1, 0x200000);
        return;
    case 3:
        temp_v0_3 = e->unk28C + 1;
        e->unk28C = temp_v0_3;
        if (!(temp_v0_3 & 7)) {
            spawn_effect(0, (s32) g_tile_effects_addr->unkA, 0, e->px, e->py, e->floor);
        }
        if (g_ent->touching == e) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            if (((temp_lo + 0xE06A02E7) / MULHI_3) == 0) {
                e->target_anim = 1;
                e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                e->ai[1] = 0x3C;
                e->bytes[0] = 1;
            } else {
                e->target_anim = 0;
                e->ai[1] = 0x14;
            }
        }
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0xA;
            return;
        }
        break;
    case 6:
        if (e->on_ground != 0) {
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_2 + 0xE06A02E7) / MULHI_41) + 0xA;
            return;
        }
        break;
    case 7:
    case 12:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            if (e->target_anim == 0xC) {
                e->target_dir = (e->target_dir + 0x10) & 0x1F;
            }
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            e->bytes[0] = 0;
            return;
        }
        break;
    case 11:
        if (e->target_anim == e->cur_anim) {
            var_v0 = 0xA;
            if (e->on_ground != 0) {
                goto block_31;
            }
        }
        break;
    }
}
