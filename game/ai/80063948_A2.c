/* 80063948: built-in program A2 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_A2(struct Entity *e) {
    s32 temp_lo;

    temp_lo = g_rng_seed * 0x7D2B89DD;
    e->target_anim = 4;
    g_rng_seed = temp_lo + 0xE06A02E7;
    e->ai[1] = ((temp_lo + 0xE06A02E7) / MULHI_31) + 0xB4;
}
