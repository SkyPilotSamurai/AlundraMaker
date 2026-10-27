/* 8006ACCC: built-in program C11 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C11(struct Entity *e) {
    s32 sp10;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s16 temp_v0_6;
    s16 var_v0_2;
    s32 temp_lo;
    s32 temp_v0_3;
    s32 temp_v1;
    s32 var_v0;
    u16 temp_v0;
    u8 temp_v0_5;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if ((temp_v0 == 0) || (e->ai[1] = temp_v0_2, ((temp_v0_2 & 0xFFFF) == 0))) {
            if ((sp10 < 6) && (sp14 < 6)) {
                if (sp18 <= 0x100000) {
                    if ((g_ent->atk_on == 0) || (g_ent->attack_addr == NULL) || (*g_ent->attack_addr == 0)) {
                        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                        e->target_anim = 1;
                        e->ai[1] = 0x12C;
                        return;
                    }
block_29:
                    e->target_anim = 3;
                    e->bytes[1] = 0xA;
                    return;
                }
                goto block_12;
            }
block_12:
            start_moving_half(e, 1, 0x12C);
            return;
        }
    default:
        return;
    case 3:
        if (e->anim_done != 0) {
            e->target_anim = 4;
            temp_v0_3 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = 0x3C;
            e->bytes[1] -= 1;
            e->target_dir = (temp_v0_3 + (((temp_lo + 0xE06A02E7) / MULHI_9) - 4)) & 0x1F;
            return;
        }
        break;
    case 4:
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF) || (e->force_adjusted != 0) || (ledge_turn(e, 4, 0x200000) != 0)) {
            temp_v0_5 = e->bytes[1] - 1;
            e->bytes[1] = temp_v0_5;
            if (temp_v0_5 & 0xFF) {
                start_moving(e, 4, 0x28, 0x1E);
                return;
            }
            var_v0 = 5;
block_40:
            e->target_anim = var_v0;
        }
        break;
    case 5:
        var_v0_2 = 0x1E;
        if (e->anim_done != 0) {
            e->target_anim = 0;
block_34:
            e->ai[1] = var_v0_2;
            return;
        }
        break;
    case 1:
        if ((sp10 < 6) && (sp14 < 6) && (sp18 <= 0x100000) && (g_ent->atk_on != 0) && (g_ent->attack_addr != NULL) && (*g_ent->attack_addr != 0)) {
            goto block_29;
        }
        temp_v0_6 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_6;
        var_v0_2 = 0x3C;
        if (!(temp_v0_6 & 0xFFFF) || (var_v0_2 = 0x3C, (e->force_adjusted != 0)) || (var_v0_2 = 0x3C, (ledge_turn(e, 1, 0x200000) != 0))) {
            e->target_anim = 0;
            goto block_34;
        }
        break;
    case 7:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            var_v0 = 3;
            if (e->bytes[1] == 0) {
                e->bytes[1] = 0xA;
                var_v0 = 3;
            }
            goto block_40;
        }
        break;
    }
}
