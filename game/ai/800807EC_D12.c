/* 800807EC: built-in program D12 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_D12(struct Entity *e) {
    s32 temp_lo;
    s32 temp_s1;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_v0;

    temp_s1 = *e->touching->attack_addr & 0xF;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
    if ((((u32) (temp_s1 - 1) < 2U) || (temp_s1 == 3)) && (temp_lo = g_rng_seed * 0x7D2B89DD, g_rng_seed = temp_lo + 0xE06A02E7, ((((temp_lo + 0xE06A02E7) / MULHI_100) < 0x46) == 0))) {
        temp_v1 = e->sprite_index;
        if (temp_v1 == 0x152) {
            var_v0 = 6;
            if ((u32) e->target_anim >= 2U) {
                goto block_6;
            }
        } else {
block_6:
            if ((temp_v1 != 0x155) || ((temp_v1_2 = e->target_anim, var_v0 = 6, (((u32) temp_v1_2 < 2U) == 0)) && (var_v0 = 6, (temp_v1_2 != 7)))) {
                goto block_9;
            }
        }
    } else {
block_9:
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        var_v0 = 4;
    }
    e->target_anim = var_v0;
}
