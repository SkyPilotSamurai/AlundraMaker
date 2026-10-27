/* 8008027C: built-in program D2 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_D2(struct Entity *e) {
    s32 temp_lo;
    s32 temp_s1;
    s32 temp_v1;
    s32 var_v0;

    temp_s1 = *e->touching->attack_addr & 0xF;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
    if (((u32) (temp_s1 - 1) < 2U) || (temp_s1 == 3)) {
        if (e->sprite_index == 0x16A) {
            temp_v1 = e->target_anim;
            var_v0 = 0xC;
            if ((u32) temp_v1 >= 2U) {
                if (temp_v1 == 0xD) {
                    var_v0 = 0xC;
                } else {
                    goto block_7;
                }
            }
        } else {
block_7:
            if ((e->sprite_index != 0x16D) || ((u32) e->target_anim >= 2U) || (temp_lo = g_rng_seed * 0x7D2B89DD, g_rng_seed = temp_lo + 0xE06A02E7, var_v0 = 0xA, ((((temp_lo + 0xE06A02E7) / MULHI_100) < 0x32) != 0))) {
                goto block_10;
            }
        }
    } else {
block_10:
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        var_v0 = 7;
    }
    e->target_anim = var_v0;
}
