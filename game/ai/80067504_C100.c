/* 80067504: built-in program C100 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void *func_8003CA78(s32, ?);                        /* extern */

void AI_C100(struct Entity *e) {
    s16 temp_v0_2;
    s32 *var_v1;
    s32 *var_v1_2;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_s2;
    s32 temp_v0_4;
    s32 temp_v1;
    s32 var_s0;
    s32 var_s0_2;
    s32 var_s0_3;
    s32 var_s0_4;
    s32 var_s0_5;
    s32 var_s1_2;
    s32 var_s2;
    struct Effect *var_t3;
    struct Effect *var_t3_2;
    u32 temp_a3;
    u32 temp_a3_2;
    void **var_s1;
    void **var_v1_3;
    void *temp_v0;
    void *temp_v0_3;
    void *temp_v0_5;
    void *temp_v0_6;
    void *var_s2_2;

    if (e->bytes[0] == 0) {
        e->bytes[0] = 1;
        var_s0 = 0;
        var_t3 = g_fx;
        var_v1 = &g_fx->spr_anim;
        do {
            temp_a0 = var_v1->unk38;
            if (temp_a0 == 2) {
                if (var_v1->unk0 == 0) {
                    *(struct Effect **)0x8012474C = var_t3;
                }
                if (var_v1->unk0 == 1) {
                    *(struct Effect **)0x80124750 = var_t3;
                }
                if (var_v1->unk0 == temp_a0) {
                    *(struct Effect **)0x80124754 = var_t3;
                }
                if (var_v1->unk0 == 3) {
                    *(struct Effect **)0x80124758 = var_t3;
                }
            }
            var_s0 += 1;
            var_v1 += 0x80;
            var_t3 += 0x80;
        } while (var_s0 != 0x80);
        var_s2 = 0xA80000;
        var_s0_2 = 0;
        var_s1 = (void **)0x8012473C;
        do {
            temp_v0 = func_8003CA78(4, 1);
            if (temp_v0 != NULL) {
                *var_s1 = temp_v0;
                temp_v0->unk40 = var_s2;
                var_s2 += 0x700000;
                temp_v0->unk3C = 0x01E00000;
                temp_v0->unk44 = 0x300001;
            }
            var_s0_2 += 1;
            var_s1 += 4;
        } while (var_s0_2 != 4);
        *(s32 *)0x8012475C = 0;
        e->flags &= ~0x80;
    }
    temp_a0_2 = *(s32 *)0x801E6378;
    if (temp_a0_2 & 1) {
        if (e->bytes[1] == 0) {
            if (e->target_anim == 0) {
                e->target_anim = 1;
                e->target_dir = 0;
                *(void *)0x8012475C = (s32) *(s32 *)0x801EF438;
            } else {
                temp_v1 = *(void *)0x801EF438;
                temp_s2 = (temp_v1 - *(void *)0x8012475C) << 0x10;
                *(void *)0x8012475C = temp_v1;
                if (temp_s2 != 0) {
                    *(s32 *)0x801E6378 = temp_a0_2 | 2;
                }
                var_s0_3 = 0;
                var_t3_2 = g_fx;
                var_v1_2 = &g_fx->y;
                do {
                    if ((var_v1_2->unk28 == 2) && (var_t3_2 != (void *)0x8012473C->unk0) && (var_t3_2 != (void *)0x8012473C->unk4) && (var_t3_2 != (void *)0x8012473C->unk8) && (var_t3_2 != (void *)0x8012473C->unkC)) {
                        var_v1_2->unk0 += temp_s2;
                    }
                    var_s0_3 += 1;
                    var_v1_2 += 0x80;
                    var_t3_2 += 0x80;
                } while (var_s0_3 < 0x80);
                temp_v0_2 = (u16) e->ai[1] + 1;
                e->ai[1] = temp_v0_2;
                if ((temp_v0_2 & 0xFFFF) == 0x130) {
                    var_s0_4 = 0;
                    var_v1_3 = (void **)0x8012473C;
                    do {
                        temp_v0_3 = *var_v1_3;
                        var_v1_3 += 4;
                        var_s0_4 += 1;
                        temp_v0_3->unk70 = 1;
                    } while (var_s0_4 != 4);
                }
                if ((u16) e->ai[1] == 0x180) {
                    *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 4);
                    e->target_anim = 0;
                    e->bytes[1] = 1;
                    e->ai[1] = 0;
                }
            }
        }
        temp_v0_4 = e->delay + 1;
        e->delay = temp_v0_4;
        if (temp_v0_4 & 7) {
            var_s1_2 = 5;
            if (e->item_state == 0) {
                var_s1_2 = 6;
                e->item_state = 6;
            }
            var_s0_5 = 0;
            var_s2_2 = NULL;
            e->item_state -= 1;
            do {
                temp_v0_5 = func_8003CA78(var_s1_2, 1);
                if (temp_v0_5 != NULL) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    temp_a3 = temp_lo + 0xE06A02E7;
                    temp_lo_2 = temp_a3 * 0x7D2B89DD;
                    temp_v0_5->unk3C = (s32) ((*(0x8012474C + (s32) var_s2_2))->unk3C + ((((temp_lo + 0xE06A02E7) / MULHI_5) << 0x13) + 0x400000));
                    temp_v0_5->unk40 = (s32) (((*(0x8012474C + (s32) var_s2_2))->unk40 - (((temp_lo_2 + 0xE06A02E7) / MULHI_15) << 0x13)) + 0xA00000);
                    g_rng_seed = temp_a3;
                    g_rng_seed = temp_lo_2 + 0xE06A02E7;
                    temp_v0_5->unk44 = (s32) ((*(0x8012474C + (s32) var_s2_2))->unk44 + 0xA00000);
                    if (var_s1_2 == 6) {
                        temp_v0_5->unk5C = 0x4000;
                        temp_v0_5->unk54 = -0x4000;
                    }
                }
                temp_v0_6 = func_8003CA78(var_s1_2, 1);
                if (temp_v0_6 != NULL) {
                    temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                    temp_a3_2 = temp_lo_3 + 0xE06A02E7;
                    temp_lo_4 = temp_a3_2 * 0x7D2B89DD;
                    temp_v0_6->unk3C = (s32) ((*(0x80124754 + (s32) var_s2_2))->unk3C + ((((temp_lo_3 + 0xE06A02E7) / MULHI_5) << 0x13) + 0xFFA80000));
                    temp_v0_6->unk40 = (s32) (((*(0x80124754 + (s32) var_s2_2))->unk40 - (((temp_lo_4 + 0xE06A02E7) / MULHI_15) << 0x13)) + 0xA00000);
                    g_rng_seed = temp_a3_2;
                    g_rng_seed = temp_lo_4 + 0xE06A02E7;
                    temp_v0_6->unk44 = (s32) ((*(0x80124754 + (s32) var_s2_2))->unk44 + 0xA00000);
                    if (var_s1_2 == 6) {
                        temp_v0_6->unk5C = 0x4000;
                        temp_v0_6->unk54 = 0x4000;
                    }
                }
                var_s0_5 += 1;
                var_s2_2 += 4;
            } while (var_s0_5 != 2);
        }
    }
}
