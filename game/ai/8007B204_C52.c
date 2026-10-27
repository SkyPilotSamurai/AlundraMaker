/* 8007B204: built-in program C52 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_C52(struct Entity *e) {
    s16 temp_v0;
    s32 temp_lo;
    struct Effect *temp_v0_2;

    if (e->target_anim == 0) {
        if (e->anim_done != 0) {
            e->target_anim = (s32) e->bytes[0];
            if (e->bytes[1] == 1) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->fz = (((temp_lo + 0xE06A02E7) / MULHI_9) << 0xB) + 0xFFFE8000;
            }
        }
    } else {
        temp_v0 = (u16) e->ai[1] + 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xF)) {
            temp_v0_2 = spawn_effect(1, 0, 0, e->px, e->py, e->pz);
            if (temp_v0_2 != NULL) {
                temp_v0_2->vz = 0x10000;
            }
        }
    }
}
