/* 8007D498: built-in program C63 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_C63(struct Entity *e) {
    s32 temp_lo;
    s32 temp_s0;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 var_a3;
    s32 var_v0;
    s32 var_v0_2;

    temp_v0 = e->unk274;
    var_v0 = temp_v0 - 1;
    if (temp_v0 == 0) {
        var_a3 = e->delay;
        e->fz = -0x30000;
        if (var_a3 == 0) {
            if (find_targets(e, 1, *e->attack_addr & 0xF, 0x80142B80, 0x80142C80) != 0) {
                var_a3 = *(s32 *)0x80142B80;
                e->delay = var_a3;
                e->item_state = var_a3->unk4;
                goto block_8;
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            var_v0 = (temp_lo + 0xE06A02E7) / MULHI_9;
            goto block_17;
        }
        if ((var_a3->unk10 != 2) || (var_a3->unk4 != e->item_state)) {
            e->delay = 0;
            return;
        }
block_8:
        temp_s0 = e->target_dir;
        temp_v0_2 = dir_from_delta(var_a3->unk114 - e->px, var_a3->unk118 - e->py);
        if (temp_s0 != temp_v0_2) {
            if (temp_v0_2 < temp_s0) {
                if ((temp_s0 - temp_v0_2) >= 4) {
                    var_v0_2 = e->target_dir - 4;
                    goto block_15;
                }
                goto block_13;
            }
            if ((temp_v0_2 - temp_s0) < 4) {
block_13:
                e->target_dir = temp_v0_2;
            } else {
                var_v0_2 = e->target_dir + 4;
block_15:
                e->target_dir = var_v0_2;
            }
            var_v0 = 2;
            goto block_17;
        }
    } else {
block_17:
        e->unk274 = var_v0;
    }
}
