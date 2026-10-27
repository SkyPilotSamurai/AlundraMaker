/* 80077D40: built-in program C80 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
extern ? D_80028AF8;

void AI_C80(struct Entity *e) {
    s16 temp_v0_3;
    s16 temp_v0_4;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_v1;
    u16 temp_v0;
    u16 temp_v0_2;
    void *temp_a0;

    select(e, 0);
    temp_a0 = *(void **)0x8013D488;
    if ((temp_a0->unk278 != 0) || (temp_a0->unk277 != 0)) {
        e->target_anim = 0;
        return;
    }
    if (e->bytes[2] == 0) {
        if (e->bytes[1] != 0) {
            if ((temp_a0->unk88 != 2) && (e->py > 0x01AFFFFF)) {
                e->bytes[1] = 0;
                e->ai[1] = 0x1E;
                goto block_12;
            }
            if (e->bytes[1] == 0) {
                goto block_9;
            }
            goto block_12;
        }
block_9:
        if ((temp_a0->unk88 == 2) || (e->py <= 0x01900000)) {
            e->bytes[1] = 1;
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            e->ai[1] = ((temp_lo + 0xE06A02E7) / 134217728) + 0x14;
            return;
        }
        goto block_12;
    }
block_12:
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        if (e->bytes[1] != 0) {
            e->target_anim = 1;
            e->target_dir = 0;
            return;
        }
        if (e->bytes[0] != 0) {
            e->bytes[0] = 0;
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 1;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->ai[1] = ((temp_lo_2 + 0xE06A02E7) / MULHI_61) + 0x3C;
            return;
        }
        temp_lo_3 = g_rng_seed * 0x7D2B89DD;
        g_rng_seed = temp_lo_3 + 0xE06A02E7;
        e->ai[1] = 0x3C;
        e->bytes[0] = 1;
        e->target_dir = (s32) *(((temp_lo_3 + 0xE06A02E7) / 1073741824) + &D_80028AF8);
        return;
    case 1:
        if (e->bytes[1] == 0) {
            temp_v0_2 = (u16) e->ai[1];
            temp_v0_3 = temp_v0_2 - 1;
            if (temp_v0_2 != 0) {
                e->ai[1] = temp_v0_3;
                if (temp_v0_3 & 0xFFFF) {
                    if (e->force_adjusted != 0) {
                        goto block_30;
                    }
                } else {
                    goto block_31;
                }
            } else {
block_30:
block_31:
                temp_lo_4 = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 0;
                g_rng_seed = temp_lo_4 + 0xE06A02E7;
                e->ai[1] = ((temp_lo_4 + 0xE06A02E7) / MULHI_31) + 0x1E;
                return;
            }
        } else {
            return;
        }
        break;
    case 16:
        temp_v0_4 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_4;
        if (!(temp_v0_4 & 0xFFFF) && (e->on_ground != 0)) {
            e->target_anim = 0x11;
            return;
        }
        break;
    case 17:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->bytes[2] = 0;
        }
        break;
    }
}
