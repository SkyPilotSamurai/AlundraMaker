/* 8006A10C: built-in program C9 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;

void AI_C9(struct Entity *e) {
    s32 sp18;
    s16 temp_v0;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 temp_v0_5;
    s16 var_v0_2;
    s32 temp_a0;
    s32 temp_lo;
    s32 temp_v0_3;
    s32 temp_v1;
    s32 var_v0;
    u16 temp_v1_2;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        e->bytes[0] = 0;
        if ((u16) e->ai[1] == 0) {
            e->ai[1] = 0x78;
        }
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (temp_v0 & 0xFFFF) {
            if ((sp18 < 3) && (sp1C < 3)) {
                e->target_anim = 3;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x6E;
                e->bytes[2] = 0;
                e->bytes[0] = 1;
                return;
            }
        default:
            return;
        }
        if (sees_player(e, &sp18, 1, 3, 0x800000) != 0) {
            temp_a0 = e->pz - g_ent->floor;
            if (temp_a0 > 0x100000) {
                e->target_anim = 9;
                e->ai[1] = (s16) (temp_a0 >> 0xF);
                e->fz = -0x8000;
                return;
            }
            if (temp_a0 < 0xFFF00000) {
                e->target_anim = 9;
                var_v0 = temp_a0;
                if (temp_a0 < 0) {
                    var_v0 = -var_v0;
                }
                e->ai[1] = (s16) (var_v0 >> 0xF);
                e->fz = 0x8000;
                return;
            }
            goto block_15;
        }
block_15:
        if ((sp18 < 7) && (sp1C < 7)) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            if (((temp_lo + 0xE06A02E7) / MULHI_3) == 0) {
                e->target_anim = 1;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0x28;
                e->bytes[1] = 1;
                return;
            }
        }
        start_moving(e, 1, 0x1E, 0x28);
        e->bytes[1] = 0;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            goto block_21;
        }
        if (e->force_adjusted != 0) {
            e->ai[1] = 0;
            if (e->bytes[1] != 0) {
                temp_v0_3 = step_or_turn(e, 1, 9, 0x500000) >> 0xF;
                if (e->target_anim == 9) {
                    e->ai[1] = (s16) temp_v0_3;
                    return;
                }
block_21:
                e->target_anim = 0;
                return;
            }
            e->target_anim = 0;
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            e->target_dir = (s32) *(&D_80028AD8 + e->target_dir);
            return;
        }
        break;
    case 3:
        temp_v1_2 = (u16) e->ai[1];
        if (temp_v1_2 != 0) {
            temp_v0_4 = temp_v1_2 - 1;
            if (e->bytes[2] == 0) {
                e->ai[1] = temp_v0_4;
                if (!(temp_v0_4 & 0xFFFF)) {
                    play_sound(0x1CD);
                    e->bytes[2] = 1;
                    var_v0_2 = 1;
block_37:
                    e->ai[1] = var_v0_2;
                }
            }
        }
        break;
    case 9:
        temp_v0_5 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_5;
        if (!(temp_v0_5 & 0xFFFF)) {
            start_moving_half(e, 1, 0x78);
            e->bytes[1] = 0;
            e->fz = 0;
            return;
        }
        break;
    case 5:
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            var_v0_2 = 0x1E;
            e->target_anim = 0;
            goto block_37;
        }
        break;
    }
}
