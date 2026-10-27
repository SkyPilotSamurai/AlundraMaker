/* 8006EEA8: built-in program C29 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_800274A4;
extern ? D_800274A8;
extern ? D_800274AC;
extern ? D_80028AF8;

void AI_C29(struct Entity *e) {
    s32 sp20;
    s16 temp_v0;
    s16 temp_v0_3;
    s16 temp_v0_5;
    s16 temp_v0_7;
    s32 temp_lo;
    s32 temp_v0_8;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_v0;
    u16 temp_v0_2;
    u16 temp_v0_6;
    u8 temp_v0_4;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 2:
        if ((u16) e->ai[1] == 0) {
            e->ai[1] = 0x78;
        }
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 4;
            return;
        }
    default:
        return;
    case 4:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x14;
block_8:
            e->bytes[0] = 0;
            return;
        }
        break;
    case 0:
        if ((e->bytes[2] == 0) && (sees_player(e, &sp20, 1, 5, 0x200000) != 0)) {
            e->target_anim = 3;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x3B;
            return;
        }
        temp_v0_2 = (u16) e->ai[1];
        temp_v0_3 = temp_v0_2 - 1;
        if ((temp_v0_2 == 0) || (e->ai[1] = temp_v0_3, ((temp_v0_3 & 0xFFFF) == 0))) {
            temp_v0_4 = e->bytes[0];
            e->bytes[0] = temp_v0_4 + 1;
            temp_v1_2 = temp_v0_4 & 0xFF;
            if (temp_v1_2 != 1) {
                if (temp_v1_2 < 2) {
                    if (temp_v1_2 != 0) {
                        e->bytes[0] = 0;
                        return;
                    }
                    e->ai[1] = 0x14;
                    var_v0 = *(&D_80028AF8 + e->anim_quadrant) + 8;
                    goto block_28;
                }
                if (temp_v1_2 != 2) {
                    e->bytes[0] = 0;
                    return;
                }
                start_moving(e, 1, 0x78, 0x14);
                e->bytes[2] = 0;
                goto block_8;
            }
            e->ai[1] = 0x14;
            var_v0 = *(&D_80028AF8 + e->anim_quadrant) + 0x10;
block_28:
            e->target_dir = var_v0 & 0x1F;
            return;
        }
        break;
    case 1:
        temp_v0_5 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_5;
        if (!(temp_v0_5 & 0xFFFF)) {
            e->target_anim = 5;
            return;
        }
        if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            var_v0 = e->target_dir + ((temp_lo + 0xE06A02E7) / MULHI_24) + 1;
            goto block_28;
        }
        break;
    case 3:
        temp_v0_6 = (u16) e->ai[1];
        temp_v0_7 = temp_v0_6 - 1;
        if (temp_v0_6 != 0) {
            e->ai[1] = temp_v0_7;
            if (!(temp_v0_7 & 0xFFFF)) {
                temp_v0_8 = e->anim_quadrant * 0xC;
                spawn_warp_entity(e, 1, 0x9B, e->px + *(&D_800274A4 + temp_v0_8), /* extra? */ (e->py + *(&D_800274A8 + temp_v0_8)), /* extra? */ (e->pz + *(&D_800274AC + temp_v0_8)), /* extra? */ e->target_dir);
            }
        }
        if (e->anim_done != 0) {
            e->target_anim = 5;
            e->bytes[2] = 1;
            return;
        }
        break;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[1] != 0) {
                e->bytes[1] = 0;
                e->px += e->delay;
                e->py += e->item_state;
            }
            e->target_anim = 2;
            return;
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 8;
                e->flags |= 0x40;
                return;
            }
            e->target_anim = 5;
            e->ai[1] = 0;
            e->bytes[1] = 0;
        }
        break;
    }
}
