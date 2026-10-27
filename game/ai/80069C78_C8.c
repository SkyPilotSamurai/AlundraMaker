/* 80069C78: built-in program C8 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AD8;

void AI_C8(struct Entity *e) {
    s32 sp20;
    s16 temp_v0;
    s16 temp_v0_3;
    s16 temp_v0_5;
    s16 temp_v0_6;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v0_4;
    s32 temp_v1;
    s32 var_s1;
    s32 var_s2;
    struct Entity *temp_v0_7;
    u16 temp_v0_2;

    rel_tile(e, &sp20);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
    case 1:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (temp_v0 & 0xFFFF) {
            if ((sp20 < 3) && (sp24 < 3) && (sp28 <= 0x100000)) {
                e->target_anim = 5;
block_34:
                e->bytes[0] = 0;
                e->ai[1] = 0x5E;
block_35:
                e->flags |= 0x40;
                return;
            }
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
block_28:
        e->target_anim = 4;
        return;
    case 2:
        temp_v0_2 = (u16) e->ai[1];
        if (temp_v0_2 != 0) {
            e->ai[1] = temp_v0_2 - 1;
            if ((sp20 < 5) && (sp24 < 5) && (sp28 <= 0x100000)) {
                e->target_anim = 3;
                e->bytes[1] = 3;
                return;
            }
            e->bytes[1] = 0;
            return;
        }
        e->target_anim = 3;
        return;
    case 3:
        if (e->anim_done != 0) {
            if (e->bytes[1] == 3) {
                e->target_anim = 0xB;
                e->bytes[1] = 0;
                e->ai[1] = 0x28;
                return;
            }
            start_moving(e, 1, 0x78, 0x1E);
            return;
        }
    default:
        return;
    case 4:
        if (e->anim_done != 0) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 2;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / MULHI_21) + 0x78;
            return;
        }
        break;
    case 11:
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (!(temp_v0_3 & 0xFFFF)) {
            e->target_anim = 6;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x78;
            e->unk28C = 0;
            return;
        }
        break;
    case 6:
        temp_v0_4 = e->unk28C + 1;
        e->unk28C = temp_v0_4;
        if (!(temp_v0_4 & 7)) {
            spawn_effect(0, (s32) g_tile_effects_addr->unkA, 0, e->px, e->py, e->floor);
        }
        temp_v0_5 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_5;
        if (!(temp_v0_5 & 0xFFFF)) {
            goto block_28;
        }
        break;
    case 8:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 9;
                goto block_35;
            }
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            if (((temp_lo_2 + 0xE06A02E7) / MULHI_5) == 2) {
                e->target_anim = 5;
                goto block_34;
            }
            e->target_anim = 4;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 5:
        if (e->bytes[0] == 0) {
            temp_v0_6 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_6;
            if (!(temp_v0_6 & 0xFFFF)) {
                e->bytes[0] = 1;
                play_sound(0x2D);
                var_s2 = 0;
                var_s1 = 4;
                do {
                    temp_v0_7 = spawn_warp_entity(e, 1, 0x8B, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x100000), /* extra? */ var_s1);
                    if (temp_v0_7 != NULL) {
                        temp_v0_7->bi_a = 0;
                        temp_v0_7->target_anim = 0xA;
                        temp_v0_7->contents_item = 0;
                    }
                    var_s2 += 1;
                    var_s1 += 8;
                } while (var_s2 != 4);
                return;
            }
        }
        break;
    case 10:
        if (e->on_ground != 0) {
            destroy_entity(e, -1);
        }
        break;
    }
}
