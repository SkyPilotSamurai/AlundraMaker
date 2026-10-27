/* 8006D928: built-in program C22 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_8003B518(struct Entity *);                   /* extern */
extern ? D_80028AD8;

void AI_C22(struct Entity *e) {
    s32 sp10;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 var_v0;
    struct Entity *temp_v1_2;
    struct Entity *temp_v1_3;
    u16 temp_v0;
    u8 temp_v0_3;
    u8 var_v0_2;

    rel_tile_z(e, &sp10);
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 7:
        if ((sp10 < 3) && (sp14 < 3)) {
            e->target_anim = 0;
            e->ai[1] = 0;
            e->bytes[1] = 1;
            return;
        }
    default:
        return;
    case 0:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if ((temp_v0 == 0) || (e->ai[1] = temp_v0_2, ((temp_v0_2 & 0xFFFF) == 0))) {
            if (e->bytes[0] == 0) {
                e->bytes[0] = 0xA;
            }
            if (e->bytes[1] == 1) {
                var_v0 = 2;
                if (e->on_ground == 0) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo + 0xE06A02E7;
                    var_v0 = ((temp_lo + 0xE06A02E7) / MULHI_3) + 1;
                }
                e->target_anim = var_v0;
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                e->target_dir = (temp_lo_2 + 0xE06A02E7) / 134217728;
                return;
            }
            if (e->force_adjusted != 0) {
                var_v0_2 = *(&D_80028AD8 + e->target_dir);
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
            } else {
                var_v0_2 = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
            }
            e->target_dir = (s32) var_v0_2;
            e->target_anim = 2;
            return;
        }
        break;
    case 1:
    case 2:
    case 3:
        if ((e->anim_done != 0) || ((e->on_ground != 0) && (e->target_anim == 3)) || (e->force_adjusted != 0)) {
            e->ai[1] = 0xA;
            e->target_anim = 0;
            temp_v0_3 = e->bytes[0] - 1;
            e->bytes[0] = temp_v0_3;
            if (!(temp_v0_3 & 0xFF)) {
                if (e->bytes[1] == 1) {
                    e->bytes[1] = 2;
                    return;
                }
                e->target_anim = 8;
                return;
            }
        }
        break;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                if (g_cur_map == 0x5F) {
                    temp_v1_2 = e->parent;
                    temp_v1_2->ai[4] = (u16) temp_v1_2->ai[4] - 1;
                }
                e->target_anim = 6;
                e->flags |= 0x40;
                return;
            }
            if (e->bytes[1] == 1) {
                e->bytes[0] = 0;
            }
            e->target_anim = 0;
            return;
        }
        break;
    case 8:
        if (e->anim_done != 0) {
            if (g_cur_map == 0x5F) {
                temp_v1_3 = e->parent;
                temp_v1_3->ai[4] = (u16) temp_v1_3->ai[4] - 1;
                remove_entity(e);
                return;
            }
            func_8003B518(e);
        }
        break;
    }
}
