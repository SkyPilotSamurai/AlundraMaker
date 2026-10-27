/* 80066B5C: built-in program C97 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void *func_8003CA78(?, ?);                          /* extern */
extern ? D_80026D4C;
extern ? D_80026D8C;
extern ? D_80026D90;

void AI_C97(struct Entity *e) {
    s32 sp10;
    s32 sp14;
    s16 temp_v0_5;
    s16 var_v0_3;
    s32 *var_a0;
    s32 *var_a0_2;
    s32 temp_a0;
    s32 temp_a1;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v0_6;
    s32 temp_v0_7;
    s32 temp_v1;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 temp_v1_6;
    s32 temp_v1_7;
    s32 temp_v1_8;
    s32 var_t2;
    s32 var_v0;
    s32 var_v0_2;
    u32 temp_a3;
    u32 temp_v0_3;
    u32 temp_v0_4;
    u32 temp_v1_2;

    if (e->unk284 == NULL) {
        e->unk284 = func_8003CA78(0, 1);
    }
    temp_v1 = *(s32 *)0x801E6378;
    if (temp_v1 & 1) {
        if (e->bytes[2] == 0) {
            if (temp_v1 & 0x80) {
                e->bytes[1] = 0;
                *(s32 *)0x801E6378 &= ~0x80;
            }
            temp_lo = g_rng_seed * 0x7D2B89DD;
            temp_v1_2 = temp_lo + 0xE06A02E7;
            temp_lo_2 = temp_v1_2 * 0x7D2B89DD;
            temp_a3 = temp_lo_2 + 0xE06A02E7;
            sp10 = temp_v1_2 * 3;
            sp14 = (temp_lo + 0xE06A02E7) / MULHI_3;
            var_t2 = 0;
            g_rng_seed = temp_v1_2;
            *(s32 *)0x80124730 = e->delay;
            *(s32 *)0x80124734 = ((temp_lo + 0xE06A02E7) / MULHI_3) + 3;
            e->ai[1] = 0x3C;
            e->ai[4] = 0;
            g_rng_seed = temp_a3;
            temp_v0 = ((temp_lo_2 + 0xE06A02E7) / MULHI_5) + 0x46;
            e->item_state = temp_v0;
            e->delay = (e->delay + temp_v0) & 0xF;
            if ((u8) e->bytes[1] >= 4U) {
                temp_lo_3 = temp_a3 * 0x7D2B89DD;
                g_rng_seed = temp_lo_3 + 0xE06A02E7;
                if (((temp_lo_3 + 0xE06A02E7) / MULHI_3) == 0) {
                    if (e->delay == 1) {
                        e->delay = 0;
                        e->item_state -= 1;
                    }
                    if (e->delay == 0xF) {
                        e->delay = 0;
                        e->item_state += 1;
                    }
                }
            }
            temp_v0_2 = e->delay;
            if (temp_v0_2 != 0) {
                temp_v0_3 = *(&D_80026D4C + (temp_v0_2 * 4)) - 0x8000;
                temp_v1_3 = (temp_v0_3 >> 3) & 0xFFC;
                if (temp_v0_3 & 0x8000) {
                    var_a0 = temp_v1_3 + 0x801E6378;
                } else {
                    var_a0 = temp_v1_3 + 0x801DD334;
                }
                temp_v1_4 = *(&D_80026D4C + (e->delay * 4)) + 0x8000;
                var_v0 = temp_v1_4;
                if (temp_v1_4 < 0) {
                    var_v0 = temp_v1_4 + 0x1F;
                }
                if (*var_a0 & (1 << (temp_v1_4 - ((var_v0 >> 5) << 5)))) {
                    var_t2 = 1;
                } else {
                    goto block_20;
                }
            } else {
block_20:
                if ((u8) e->bytes[1] < 2U) {
                    temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                    g_rng_seed = temp_lo_4 + 0xE06A02E7;
                    if (((temp_lo_4 + 0xE06A02E7) / MULHI_3) == 0) {
                        temp_a1 = (e->delay + 1) & 0xF;
                        if (temp_a1 != 0) {
                            temp_v0_4 = *(&D_80026D4C + (temp_a1 * 4)) - 0x8000;
                            temp_v1_5 = (temp_v0_4 >> 3) & 0xFFC;
                            if (temp_v0_4 & 0x8000) {
                                var_a0_2 = temp_v1_5 + 0x801E6378;
                            } else {
                                var_a0_2 = temp_v1_5 + 0x801DD334;
                            }
                            temp_v1_6 = *(&D_80026D4C + (temp_a1 * 4)) + 0x8000;
                            var_v0_2 = temp_v1_6;
                            if (temp_v1_6 < 0) {
                                var_v0_2 = temp_v1_6 + 0x1F;
                            }
                            if (*var_a0_2 & (1 << (temp_v1_6 - ((var_v0_2 >> 5) << 5)))) {
                                var_t2 = 1;
                                e->delay = temp_a1;
                                e->item_state += 1;
                            }
                        }
                    }
                }
            }
            if (var_t2 != 0) {
                *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 0x100);
            } else {
                *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 & ~0x100);
            }
            e->bytes[2] = 1;
        }
        temp_v0_5 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_5;
        if (!(temp_v0_5 & 0xFFFF)) {
            if (e->item_state == 0) {
                e->bytes[2] = 0;
                e->bytes[1] += 1;
                temp_v1_7 = *(void *)0x801E6378;
                *(void *)0x801E6378 = (s32) (temp_v1_7 & ~1);
                if (temp_v1_7 & 0x100) {
                    play_sound(0x1C6);
                    return;
                }
                play_sound(0x1C7);
                return;
            }
            temp_v0_6 = (*(void *)0x80124730 + 1) & 0xF;
            *(void *)0x80124730 = temp_v0_6;
            temp_v0_7 = temp_v0_6 * 8;
            e->item_state -= 1;
            e->ai[4] = (u16) e->ai[4] + 1;
            e->unk284->unk3C = (s32) *(&D_80026D8C + temp_v0_7);
            e->unk284->unk40 = (s32) *(&D_80026D90 + temp_v0_7);
            play_sound(0x1C8);
            temp_a0 = e->item_state;
            temp_v1_8 = *(void *)0x80124734;
            if (temp_v1_8 < temp_a0) {
                if ((u16) e->ai[4] >= 5U) {
                    var_v0_3 = 6;
                } else {
                    goto block_43;
                }
            } else if ((u16) e->ai[4] < 5U) {
block_43:
                var_v0_3 = 0x24 - ((u16) e->ai[4] * 6);
            } else {
                var_v0_3 = ((temp_v1_8 - temp_a0) * 8) + 8;
            }
            e->ai[1] = var_v0_3;
        }
    }
}
