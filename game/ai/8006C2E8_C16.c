/* 8006C2E8: built-in program C16 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C16(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_v0_6;
    s32 temp_v1;
    s32 var_hi;
    u16 temp_v0;
    u8 temp_v0_3;
    u8 temp_v0_4;
    u8 temp_v0_5;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 == 0) {
            start_moving(e, 1, 0x78, 0x46);
            e->bytes[1] = 0;
            return;
        }
        e->ai[1] = temp_v0 - 1;
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            temp_v0_3 = e->bytes[1];
            if (temp_v0_3 != 0) {
                e->bytes[1] = temp_v0_3 - 1;
                temp_lo = g_rng_seed * 0x7D2B89DD;
                var_hi = (temp_lo + 0xE06A02E7) / 134217728;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->ai[1] = 0x78;
                goto block_18;
            }
            e->target_anim = 0;
            e->ai[1] = 0x14;
            e->bytes[0] = 0;
            return;
        }
        if (sees_player(e, &sp18, 3, 3, 0) != 0) {
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            if (((temp_lo_2 + 0xE06A02E7) / MULHI_5) == 0) {
                play_sound(0x94);
            }
block_29:
            e->target_anim = 7;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->unk28C = 0;
        } else {
            if (e->force_adjusted != 0) {
                temp_v0_4 = e->bytes[1];
                if (temp_v0_4 != 0) {
                    e->bytes[1] = temp_v0_4 - 1;
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    var_hi = (temp_lo_3 + 0xE06A02E7) / 134217728;
                    g_rng_seed = temp_lo_3 + 0xE06A02E7;
                    e->ai[1] = 0x78;
                    goto block_18;
                }
                temp_v0_5 = e->bytes[0] + 1;
                e->bytes[0] = temp_v0_5;
                if ((u32) (temp_v0_5 & 0xFF) < 4U) {
                    e->target_anim = 0;
                    return;
                }
                e->bytes[0] = 0;
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                var_hi = (temp_lo_4 + 0xE06A02E7) / 134217728;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                e->ai[1] = 0x78;
                e->bytes[1] = 3;
block_18:
                e->target_dir = var_hi >> 0;
                return;
            }
        default:
            return;
        }
        break;
    case 3:
        temp_v0_6 = e->unk28C + 1;
        e->unk28C = temp_v0_6;
        if (!(temp_v0_6 & 7)) {
            spawn_effect(0, (s32) g_tile_effects_addr->unkA, 0, e->px, e->py, e->floor);
        }
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 6:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x14;
            e->target_dir = (e->target_dir + 0x10) & 0x1F;
            return;
        }
        break;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            goto block_29;
        }
        break;
    }
}
