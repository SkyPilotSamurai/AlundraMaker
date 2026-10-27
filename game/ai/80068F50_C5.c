/* 80068F50: built-in program C5 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C5(struct Entity *e) {
    s32 sp10;
    s16 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_4;
    u8 temp_a0;
    u8 temp_v1_2;
    u8 var_v0;

    rel_tile(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1 */
    case 0:                                         /* switch 1 */
        if (e->on_ground != 0) {
            if ((u32) (e->bytes[1] - 3) < 5U) {
                temp_v0 = (u16) e->ai[1];
                temp_v0_2 = temp_v0 - 1;
                if ((temp_v0 == 0) || (e->ai[1] = temp_v0_2, ((temp_v0_2 & 0xFFFF) == 0))) {
                    temp_a0 = e->bytes[1];
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->target_anim = 3;
                    e->delay = 0;
                    if ((temp_a0 & 0xFF) == 6) {
                        e->bytes[1] = 0;
                        return;
                    }
                    var_v0 = temp_a0 + 1;
                    goto block_37;
                }
            } else {
                e->ai[1] = 0;
                e->bytes[1] = 0;
            case 1:                                 /* switch 1 */
                temp_v0_3 = e->item_state;
                if (temp_v0_3 != 0) {
                    e->item_state = temp_v0_3 - 1;
                }
                temp_v0_4 = (u16) e->ai[1];
                if (temp_v0_4 == 0) {
                    e->target_anim = 1;
                    e->ai[1] = 0xF0;
                    if (near_in_front(e, &sp10, 6, 0x100000) != 0) {
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        var_v0 = 1;
                    } else {
                        start_moving(e, 1, 0xB4, 0x14);
                        var_v0 = 2;
                    }
block_37:
                    e->bytes[1] = var_v0;
                } else {
                    e->ai[1] = temp_v0_4 - 1;
                    if (e->force_adjusted != 0) {
                        step_or_turn(e, 1, 4, 0x100000);
                        return;
                    }
                    if ((e->item_state == 0) && (sp10 < 3) && (sp14 < 3) && (sp18 <= 0x100000)) {
                        temp_v1_2 = e->bytes[1];
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        switch (temp_v1_2) {        /* switch 2; irregular */
                        case 1:                     /* switch 2 */
                            e->target_anim = 3;
                            e->delay = 0;
                            return;
                        case 2:                     /* switch 2 */
                            e->bytes[1] = 7;
                            e->ai[1] = 0x3C;
                            e->target_anim = 0;
                            return;
                        }
                    }
                }
            }
        } else {
        default:                                    /* switch 1 */
            return;
        }
        break;
    case 3:                                         /* switch 1 */
        if (g_ent->touching == e) {
            e->delay = 1;
        }
        if (e->anim_done != 0) {
            if (e->delay != 0) {
                e->target_anim = 0;
                e->ai[1] = 0x1E;
                e->delay = 0;
                return;
            }
            start_moving_half(e, 1, 0x78);
            e->item_state = (s32) (u16) e->ai[1];
            return;
        }
        break;
    case 6:                                         /* switch 1 */
    case 11:                                        /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
                return;
            }
            e->ai[1] = 0xA;
            e->target_anim = 0;
            e->target_dir = (e->target_dir + 0x10) & 0x1F;
            if ((u32) (e->bytes[1] - 3) >= 4U) {
                var_v0 = 3;
                goto block_37;
            }
        }
        break;
    }
}
