/* 8006BD58: built-in program C14 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AF8;

void AI_C14(struct Entity *e) {
    s32 sp18;
    s16 temp_v0;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_v1;
    s32 var_v0;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_lo = g_rng_seed * 0x7D2B89DD;
        e->target_anim = 1;
        g_rng_seed = temp_lo + 0xE06A02E7;
        e->ai[1] = ((temp_lo + 0xE06A02E7) / 268435456) + 0xB4;
        return;
    case 1:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0x1F)) {
            if ((sp18 < 5) && (sp1C < 5) && (g_ent->atk_on != 0)) {
                if ((g_ent->attack_addr != NULL) && (*g_ent->attack_addr != 0)) {
                    e->target_anim = 8;
                    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                    return;
                }
                goto block_11;
            }
block_11:
            if (sees_player(e, &sp18, 1, 8, 0x100000) != 0) {
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->target_anim = 3;
                e->ai[1] = 0xB4;
                return;
            }
            goto block_13;
        }
block_13:
        if ((u16) e->ai[1] == 0) {
            e->target_anim = 0;
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            var_v0 = *(&D_80028AF8 + e->anim_quadrant) - 8;
block_21:
            e->target_dir = var_v0 & 0x1F;
            return;
        }
        if (e->force_adjusted != 0) {
            step_or_turn(e, 1, 2, 0x300000);
            return;
        }
        ledge_turn(e, 1, 0x300000);
        return;
    case 3:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (temp_v0_2 & 0xFFFF) {
            if (e->force_adjusted != 0) {
                e->target_anim = 8;
                var_v0 = e->target_dir - 0x10;
                goto block_21;
            }
        } else {
block_27:
            e->target_anim = 0;
        default:
            return;
        }
        break;
    case 7:
    case 9:
        if (e->on_ground != 0) {
            e->target_anim = 0;
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
            goto block_27;
        }
        break;
    }
}
