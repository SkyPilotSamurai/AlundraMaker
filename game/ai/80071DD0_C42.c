/* 80071DD0: built-in program C42 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
void AI_C42(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 temp_v0_7;
    s16 temp_v0_8;
    s32 temp_v0;
    s32 temp_v0_4;
    s32 temp_v1;
    struct Entity *temp_s1;
    struct Entity *temp_v0_5;
    u16 temp_v0_6;
    u8 temp_v0_9;
    u8 temp_v1_2;
    u8 temp_v1_3;
    u8 temp_v1_4;

    temp_s1 = e->parent;
    if (temp_s1->bytes[3] != 0) {
        temp_v1 = e->target_anim;
        if ((temp_v1 != 8) && (temp_v1 != 4)) {
            e->target_anim = 7;
            e->flags |= 0x40;
            return;
        }
        goto block_44;
    }
    rel_tile(e, &sp20);
    temp_v0 = e->target_anim;
    switch (temp_v0) {                              /* switch 1 */
    case 8:                                         /* switch 1 */
        if (temp_s1->bytes[2] == e->bytes[2]) {
            temp_v0_2 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_2;
            if (!(temp_v0_2 & 0xFFFF)) {
                e->target_anim = 2;
                return;
            }
        } else {
block_44:
            remove_entity(e);
        default:                                    /* switch 1 */
            return;
        }
        break;
    case 4:                                         /* switch 1 */
        temp_v1_2 = temp_s1->bytes[2];
        if (temp_v1_2 == e->bytes[2]) {
            if ((temp_v1_2 == 4) && ((temp_v0_3 = (u16) e->ai[1] - 1, e->ai[1] = temp_v0_3, ((temp_v0_3 & 0xFFFF) == 0)) || (e->force_adjusted != 0))) {
                e->target_anim = 8;
                e->ai[1] = (s16) e->delay;
                return;
            }
        } else {
            goto block_44;
        }
        break;
    case 2:                                         /* switch 1 */
        if (e->anim_done != 0) {
            temp_v1_3 = e->bytes[2];
            if ((temp_v1_3 == 3) || (temp_v1_3 == 1)) {
                e->target_anim = 3;
            }
            if (e->bytes[2] == 5) {
                play_sound(0x6E);
                e->target_anim = 1;
                e->bytes[0] = 6;
            }
            if (e->bytes[2] == 4) {
                e->target_anim = 1;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                return;
            }
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v0_4 = e->delay + 1;
        e->delay = temp_v0_4;
        if (!(temp_v0_4 & 7)) {
            temp_v0_5 = spawn_warp_entity(e, 1, 0xE4, e->px, /* extra? */ (e->py + 0xFFFF0000), /* extra? */ e->pz, /* extra? */ 0);
            if (temp_v0_5 != NULL) {
                temp_v0_5->target_anim = 2;
                temp_v0_5->flags = (temp_v0_5->flags & ~3) | 0x40;
            }
        }
        temp_v1_4 = e->bytes[2];
        switch (temp_v1_4) {                        /* switch 2; irregular */
        case 4:                                     /* switch 2 */
            if (temp_s1->target_anim != 3) {
                if (e->bytes[0] != 5) {
                    temp_v0_6 = (u16) e->ai[1];
                    temp_v0_7 = temp_v0_6 - 1;
                    if ((temp_v0_6 == 0) || (e->ai[1] = temp_v0_7, ((temp_v0_7 & 0xFFFF) == 0))) {
                        e->ai[1] = 8;
                        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        e->bytes[0] += 1;
                        return;
                    }
                } else if (e->force_adjusted != 0) {
                    goto block_38;
                }
            } else {
block_37:
block_38:
                e->target_anim = 0xA;
                return;
            }
            break;
        case 5:                                     /* switch 2 */
            temp_v0_8 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_8;
            if (temp_v0_8 & 0xFFFF) {
                if (e->force_adjusted != 0) {
                    goto block_37;
                }
                temp_v0_9 = e->bytes[0] - 1;
                e->bytes[0] = temp_v0_9;
                if (!(temp_v0_9 & 0xFF)) {
                    e->bytes[0] = 6;
                    e->target_dir = (e->target_dir + 1) & 0x1F;
                    return;
                }
            } else {
                goto block_38;
            }
            break;
        }
        break;
    case 3:                                         /* switch 1 */
    case 10:                                        /* switch 1 */
        if (e->anim_done != 0) {
            e->target_anim = 9;
            return;
        }
        break;
    case 9:                                         /* switch 1 */
        if (e->anim_done != 0) {
            goto block_44;
        }
        break;
    }
}
