/* 8006BA1C: built-in program C13 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C13(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 temp_v0_4;
    s32 temp_v1;
    u16 temp_v0;
    u8 temp_s1;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0_2;
            if (!(temp_v0_2 & 0xFFFF) && (e->bytes[1] == 1)) {
                e->target_anim = 3;
                return;
            }
        default:
            return;
        }
        if (sp18 < 5) {
            if ((sp1C >= 5) || (sp20 > 0x200000)) {
                goto block_10;
            }
block_14:
            e->bytes[1] = 1;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[1] = 0x1E;
            return;
        }
block_10:
        if (sees_player(e, &sp18, 1, 0xA, 0x200000) == 0) {
            start_moving(e, 1, 0xB4, 0x46);
            return;
        }
block_16:
        e->target_anim = 9;
        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        e->ai[1] = 0xB4;
        return;
    case 1:
        temp_v0_3 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_3;
        if (temp_v0_3 & 0xFFFF) {
            if (sees_player(e, &sp18, 2, 3, 0x300000) != 0) {
                goto block_14;
            }
            if (sees_player(e, &sp18, 1, 5, 0x200000) != 0) {
                goto block_16;
            }
            if (e->force_adjusted != 0) {
                step_or_turn(e, 1, 2, 0x300000);
                return;
            }
            ledge_turn(e, 1, 0x300000);
            return;
        }
block_21:
        e->target_anim = 0;
        return;
    case 9:
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF)) {
            goto block_21;
        }
        if (e->force_adjusted != 0) {
            e->target_anim = 8;
            e->target_dir = (e->target_dir - 0x10) & 0x1F;
            return;
        }
        temp_s1 = (u8) e->unk8C;
        if (ledge_turn(e, 1, 0) != 0) {
            e->target_dir = (s32) temp_s1;
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 7:
        if (e->on_ground != 0) {
            if (e->bytes[1] == 1) {
                e->target_anim = 9;
                e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
                e->ai[1] = 0x78;
block_34:
                e->bytes[1] = 0;
            } else {
                e->target_anim = 0;
                e->ai[1] = 0;
                return;
            }
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
            e->ai[1] = 0;
            goto block_34;
        }
        break;
    }
}
