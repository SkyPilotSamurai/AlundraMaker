/* 8006D640: built-in program C21 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
extern ? D_80028AF8;

void AI_C21(struct Entity *e) {
    s32 sp18;
    s16 temp_v0;
    s16 temp_v0_2;
    s32 temp_lo;
    s32 temp_v0_3;
    s32 temp_v1;

    rel_tile(e, &sp18);
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        if ((u16) e->ai[1] == 0) {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = 0x3C;
            e->target_dir = (temp_lo + 0xE06A02E7) / 134217728;
        }
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            if (e->bytes[0] != 0) {
                e->target_anim = 3;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->bytes[0] = 0;
                e->unk28C = 0;
                return;
            }
            e->target_anim = 1;
            e->ai[1] = 0x78;
            return;
        }
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (temp_v0_2 & 0xFFFF) {
            if ((sp18 < 3) && (sp1C < 3) && (sp20 == 0)) {
                e->bytes[0] = 1;
                e->target_anim = 0;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->ai[1] = 0xA;
                return;
            }
            if ((e->force_adjusted != 0) || (ledge_ahead(e, 0) != 0)) {
                e->sfy = 0;
                e->sfx = 0;
                e->fy = 0;
                e->fx = 0;
                e->tfy = 0;
                e->tfx = 0;
                e->target_dir = (*(&D_80028AF8 + e->anim_quadrant) - 0x10) & 0x1F;
                return;
            }
        } else {
block_29:
            e->target_anim = 0;
        }
        break;
    case 5:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                return;
            }
            e->bytes[0] = 1;
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        break;
    case 3:
        temp_v0_3 = e->unk28C + 1;
        e->unk28C = temp_v0_3;
        if (!(temp_v0_3 & 7)) {
            spawn_effect(0, (s32) g_tile_effects_addr->unkA, 0, e->px, e->py, e->floor);
        }
        if ((e->anim_done != 0) || (e->force_adjusted != 0)) {
            goto block_29;
        }
        break;
    }
}
