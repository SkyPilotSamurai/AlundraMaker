/* 8006F9F8: built-in program C31 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80027520;
extern ? D_80027524;
extern ? D_80027528;
extern ? D_80028AD8;
extern ? D_80028AF8;

void AI_C31(struct Entity *e) {
    s32 sp20;
    s16 temp_v0_4;
    s16 temp_v0_6;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_lo;
    s32 temp_v0_7;
    s32 var_a1;
    s32 var_v0;
    struct Entity *temp_v0_8;
    u16 temp_v0;
    u16 temp_v0_5;
    u32 temp_v0_3;
    u32 temp_v0_9;
    u8 temp_v0_2;

    rel_tile(e, &sp20);
    if (((u32) e->target_anim < 2U) && (sp20 < 4) && (sp24 < 4) && (sp28 <= 0x100000)) {
        e->target_anim = 3;
        e->cur_anim = -1;
        e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        e->ai[1] = 0x20;
        return;
    }
    temp_a0 = e->target_anim;
    switch (temp_a0) {                              /* switch 1; irregular */
    case 0:                                         /* switch 1 */
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        if (e->bytes[1] != 0) {
            temp_v0_2 = e->bytes[1];
            e->ai[1] = 0x3C;
            temp_a0_2 = temp_v0_2 & 0xFF;
            e->bytes[1] = temp_v0_2 + 0xFF;
            switch (temp_a0_2) {                    /* switch 2; irregular */
            case 0:                                 /* switch 2 */
                e->target_anim = 1;
                /* fallthrough */
            case 1:                                 /* switch 2 */
                var_v0 = e->target_dir + 0x10;
block_31:
                e->target_dir = var_v0 & 0x1F;
                return;
            case 2:                                 /* switch 2 */
                temp_v0_3 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                g_rng_seed = temp_v0_3;
                var_a1 = 0xF8;
                if (((s32) MULTU_HI(temp_v0_3, temp_a0_2) >> 0) != 0) {
                    var_a1 = 8;
                }
                e->target_dir = var_a1 + *(&D_80028AF8 + e->anim_quadrant);
                return;
            }
        } else {
            start_moving(e, 1, 0x50, 0x1E);
            return;
        }
        break;
    case 1:                                         /* switch 1 */
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF)) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / 134217728) + 0x1E;
            return;
        }
        if (e->force_adjusted != 0) {
            e->sfy = 0;
            e->sfx = 0;
            e->fy = 0;
            e->fx = 0;
            e->tfy = 0;
            e->tfx = 0;
            var_v0 = *(&D_80028AD8 + e->target_dir) + 0x10;
            goto block_31;
        }
        if (ledge_ahead(e, 0) != 0) {
            e->target_anim = 0;
            e->ai[1] = 0;
            e->bytes[1] = 2;
            return;
        }
        return;
    case 3:                                         /* switch 1 */
        temp_v0_5 = (u16) e->ai[1];
        temp_v0_6 = temp_v0_5 - 1;
        if (temp_v0_5 != 0) {
            e->ai[1] = temp_v0_6;
            if (!(temp_v0_6 & 0xFFFF)) {
                temp_v0_7 = e->anim_quadrant * 0xC;
                temp_v0_8 = spawn_warp_entity(e, 1, 0xB0, e->px + *(&D_80027520 + temp_v0_7), /* extra? */ (e->py + *(&D_80027524 + temp_v0_7)), /* extra? */ (e->pz + *(&D_80027528 + temp_v0_7)), /* extra? */ e->target_dir);
                if (temp_v0_8 != NULL) {
                    temp_v0_8->fz = 0x20000;
                }
                e->bytes[0] = 0;
            }
        }
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 5:                                         /* switch 1 */
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            temp_v0_9 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
            g_rng_seed = temp_v0_9;
            if (((s32) MULTU_HI(temp_v0_9, temp_a0) >> 0) == 0) {
                play_sound(0x9E);
            }
            e->target_anim = 1;
            e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
            e->ai[1] = 0x28;
            e->bytes[0] = 1;
            e->bytes[1] = 0;
        }
        break;
    }
}
