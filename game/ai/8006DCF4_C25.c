/* 8006DCF4: built-in program C25 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C25(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_4;
    s16 temp_v0_6;
    s16 var_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_s0;
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_5;
    u8 temp_v1_2;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 3:
        if ((sp20 < 5) && (sp24 < 5) && (sp28 <= 0x100000)) {
            e->target_anim = 4;
            return;
        }
    default:
        return;
    case 4:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            return;
        }
        break;
    case 0:
        temp_v0 = (u16) e->ai[1];
        var_v0 = temp_v0 - 1;
        if (temp_v0 == 0) {
            if ((sp20 < 3) && (sp24 < 3)) {
                e->target_anim = 5;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
block_18:
                e->ai[1] = 0x10;
                e->bytes[1] = 0;
                return;
            }
            start_moving(e, 1, 0x3C, 0x64);
            return;
        }
block_41:
        e->ai[1] = var_v0;
        break;
    case 1:
        temp_v0_2 = e->item_state;
        temp_v0_3 = temp_v0_2 - 1;
        if (((temp_v0_2 == 0) || (e->item_state = temp_v0_3, (temp_v0_3 == 0))) && (sp20 < 3) && (sp24 < 3)) {
            e->target_anim = 5;
            goto block_18;
        }
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF)) {
            temp_v1_2 = e->bytes[1] + 1;
            e->bytes[1] = temp_v1_2;
            if (((u8) e->bytes[0] >= 3U) || ((u32) (temp_v1_2 & 0xFF) >= 5U)) {
                e->target_anim = 0xA;
                e->bytes[1] = 0;
                e->bytes[0] = 0;
                return;
            }
            start_moving_half(e, 1, 0x3C);
            return;
        }
        if (e->force_adjusted != 0) {
            e->bytes[0] += 1;
            step_or_turn(e, 1, 2, 0x100000);
            return;
        }
        ledge_turn(e, 1, 0x100000);
        return;
    case 10:
        if (e->anim_done != 0) {
            e->target_anim = 3;
            return;
        }
        break;
    case 5:
        temp_v0_5 = (u16) e->ai[1];
        temp_v0_6 = temp_v0_5 - 1;
        if (temp_v0_5 != 0) {
            e->ai[1] = temp_v0_6;
            if (!(temp_v0_6 & 0xFFFF)) {
                temp_s0 = e->pz + 0x200000;
                spawn_warp_entity(e, 1, 0xBC, e->px, /* extra? */ e->py, /* extra? */ temp_s0, /* extra? */ e->target_dir);
                spawn_warp_entity(e, 1, 0xBC, e->px, /* extra? */ e->py, /* extra? */ temp_s0, /* extra? */ ((e->target_dir + 8) & 0x1F));
                spawn_warp_entity(e, 1, 0xBC, e->px, /* extra? */ e->py, /* extra? */ temp_s0, /* extra? */ ((e->target_dir + 0x10) & 0x1F));
                spawn_warp_entity(e, 1, 0xBC, e->px, /* extra? */ e->py, /* extra? */ temp_s0, /* extra? */ ((e->target_dir + 0x18) & 0x1F));
            }
        }
        if (e->anim_done != 0) {
            if (e->delay == 0) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                if (((temp_lo + 0xE06A02E7) / 1073741824) == 0) {
                    e->cur_anim = -1;
                    e->ai[1] = 0x10;
                    e->delay = 1;
                    return;
                }
            }
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->delay = 0;
            e->target_anim = 1;
            e->item_state = 0x1E;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            var_v0 = ((temp_lo_2 + 0xE06A02E7) / 268435456) + 0x1E;
            goto block_41;
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            var_v0 = 0x28;
            e->target_anim = 0;
            goto block_41;
        }
        break;
    }
}
