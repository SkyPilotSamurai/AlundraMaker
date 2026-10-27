/* 80082428: built-in program E28 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
extern s16 D_80023654;
extern ? D_80023694;

void AI_E28(struct Entity *e) {
    s16 *var_s2;
    s16 temp_a1;
    s32 temp_lo;
    s32 temp_t2;
    s32 temp_v0;
    s32 var_s0;
    u32 temp_a2;

    var_s0 = 0;
    var_s2 = &D_80023654;
    do {
        temp_lo = g_rng_seed * 0x7D2B89DD;
        temp_a2 = temp_lo + 0xE06A02E7;
        temp_v0 = ((temp_lo + 0xE06A02E7) / MULHI_6145) + 0x320;
        temp_t2 = *(&D_80023694 + (var_s0 * 8)) * temp_v0;
        temp_a1 = *var_s2;
        var_s2 += 8;
        g_rng_seed = temp_a2;
        var_s0 += 1;
        spawn_effect(0, 0x13, 2, e->px + (temp_a1 * temp_v0), e->py + temp_t2, e->pz, /* extra? */ (temp_a2 * 0x1801), /* extra? */ ((temp_lo + 0xE06A02E7) / MULHI_6145));
    } while (var_s0 < 8);
    destroy_entity(e, -1);
}
