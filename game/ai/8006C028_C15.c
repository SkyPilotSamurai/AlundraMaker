/* 8006C028: built-in program C15 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AF8;

void AI_C15(struct Entity *e) {
    s32 sp18;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    u16 temp_a0;
    u8 temp_v0;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
    case 1:
        if (e->bytes[0] != 0) {
            e->target_anim = 3;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            return;
        }
        if (e->bytes[1] == 0) {
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            e->bytes[1] = 4;
            e->target_dir = (*(&D_80028AF8 + e->anim_quadrant) - 8) & 0x1F;
        }
        temp_a0 = (u16) e->ai[1];
        e->target_anim = 1;
        if (temp_a0 == 0) {
            e->ai[1] = 0x1E;
            if (sees_player(e, &sp18, 2, 2, 0) != 0) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                if (((temp_lo + 0xE06A02E7) / MULHI_5) == 0) {
                    play_sound(0x94);
                }
                e->bytes[0] = 3;
                return;
            }
        } else {
            e->ai[1] = temp_a0 - 1;
            if (e->force_adjusted != 0) {
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                e->bytes[1] -= 1;
                e->target_dir = (*(&D_80028AF8 + e->anim_quadrant) - 0x10) & 0x1F;
                return;
            }
        default:
            return;
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            temp_v0 = e->bytes[0] - 1;
            e->bytes[0] = temp_v0;
            if (!(temp_v0 & 0xFF)) {
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 0;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->ai[1] = 0;
                e->bytes[1] = 0;
                e->target_dir = ((temp_lo_2 + 0xE06A02E7) / 1073741824) * 8;
                return;
            }
            e->cur_anim = -1;
            return;
        }
        break;
    case 5:
    case 6:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            if ((sp18 < 2) && (sp1C < 2)) {
                e->bytes[0] = 3;
            }
            e->target_anim = 0;
        }
        break;
    }
}
