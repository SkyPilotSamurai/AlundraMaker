/* 800770BC: built-in program C82 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_C82(struct Entity *e) {
    s16 temp_v0;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 var_s2;
    struct Entity *temp_s1;
    struct Entity *temp_s1_2;
    struct Entity *temp_s1_3;
    u32 temp_a2;

    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        if ((u16) e->ai[1] == 0) {
            temp_s1 = e->parent;
            e->ai[1] = 0x258;
            temp_s1->ai[4] = (u16) temp_s1->ai[4] + 3;
            return;
        }
        return;
    case 1:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 4;
            return;
        }
        break;
    case 2:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                temp_s1_2 = e->parent;
                e->target_anim = 3;
                e->flags |= 0x40;
                temp_s1_2->ai[4] = (u16) temp_s1_2->ai[4] - 3;
                return;
            }
            e->target_anim = 1;
            return;
        }
        break;
    case 4:
        var_s2 = 0;
        if (e->anim_done != 0) {
            temp_s1_3 = e->parent;
            e->estatus = 3;
            do {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                temp_a2 = temp_lo + 0xE06A02E7;
                temp_lo_2 = temp_a2 * 0x7D2B89DD;
                var_s2 += 1;
                g_rng_seed = temp_a2;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                spawn_warp_entity(temp_s1_3, 1, 0xCA, e->px + (((temp_lo + 0xE06A02E7) / MULHI_25) << 0x10) + 0xFFF40000, /* extra? */ (e->py + (((temp_lo_2 + 0xE06A02E7) / MULHI_17) << 0x10) + 0xFFF40000), /* extra? */ e->pz, /* extra? */ 0);
            } while (var_s2 != 3);
        }
        break;
    }
}
