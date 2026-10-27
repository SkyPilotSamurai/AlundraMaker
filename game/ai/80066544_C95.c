/* 80066544: built-in program C95 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
extern ? D_80026CFC;
extern ? D_80026D2C;
extern ? D_80026D40;

void AI_C95(struct Entity *e) {
    s16 temp_t0;
    s16 temp_t0_2;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_v0_3;
    s32 temp_v0_4;
    s32 var_s1;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v1;
    struct Entity *temp_v0;
    struct Entity *temp_v0_2;
    struct Entity *temp_v0_5;
    u16 temp_v1;
    u8 temp_v0_6;
    u8 temp_v1_2;

    if (*(s32 *)0x801E6378 & 1) {
        if ((u16) e->ai[4] == 0) {
            e->ai[1] = 0;
            e->bytes[2] = 0;
            e->bytes[0] = 0;
            e->ai[4] = 1;
            *(s32 *)0x80124728 = 0;
            *(s32 *)0x80124724 = *(&D_80026D2C + (e->bytes[1] * 4));
            e->delay = 0x64;
            if ((u32) (e->bytes[1] - 1) < 2U) {
                temp_v0 = SpawnMapEntity(e, 0, 1);
                temp_v0->target_dir = 0x18;
                if (e->bytes[1] == 1) {
                    temp_v0->delay = 0x20000;
                } else {
                    temp_v0->delay = 0x28000;
                }
            }
            *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 & ~0x100);
        }
        var_s1 = 0;
        e->ai[1] = (u16) e->ai[1] + 1;
        temp_v1 = (u16) e->ai[1];
        temp_a0 = e->delay + 1;
        e->delay = temp_a0;
        if (temp_v1 < 0x258U) {
            var_s1 = (temp_a0 >= 0x78) * 2;
            goto block_19;
        }
        var_v0 = temp_a0 < 0x64;
        if ((temp_v1 < 0x3C0U) || (var_v0 = temp_a0 < 0x78, ((temp_v1 < 0x4ECU) != 0)) || (var_v0 = temp_a0 < 0x50, ((temp_v1 < 0x744U) != 0))) {
            if (var_v0 == 0) {
                var_s1 = 2;
            }
block_19:
            if (var_s1 != 0) {
                temp_v0_2 = SpawnMapEntity(e, var_s1, 1);
                temp_v0_2->contents_item = 0;
                temp_v0_2->flags = (temp_v0_2->flags & 0xFFF8FFFF) | 0x30000;
                if (var_s1 != 0) {
                    temp_v0_3 = *(void *)0x80124728;
                    e->delay = 0;
                    if (temp_v0_3 == 0) {
                        temp_lo = g_rng_seed * 0x7D2B89DD;
                        *(void *)0x80124728 = 3;
                        g_rng_seed = temp_lo + 0xE06A02E7;
                        *(s32 *)0x8012472C = (temp_lo + 0xE06A02E7) / MULHI_6;
                    } else {
                        *(void *)0x80124728 = (s32) (temp_v0_3 - 1);
                    }
                    temp_t0 = *((*(void *)0x80124728 * 2) + ((*(void *)0x8012472C * 8) + &D_80026CFC));
                    if (temp_t0 & 1) {
                        temp_v0_2->pz += 0x180000;
                        temp_v0_2->delay = *(void *)0x80124724 + 0x14000;
                        if (!(temp_t0 & 2)) {
                            temp_v0_2->target_dir = 0x18;
                        } else {
                            var_v0_2 = 8;
                            goto block_31;
                        }
                    } else {
                        temp_v0_2->delay = *(void *)0x80124724 + 0x12000;
                        if (!(temp_t0 & 2)) {
                            temp_v0_2->target_dir = 8;
                        } else {
                            var_v0_2 = 0x18;
block_31:
                            temp_v0_2->target_dir = var_v0_2;
                            temp_v0_2->py += 0xFFF00000;
                        }
                    }
                    if (temp_v0_2->target_dir == 8) {
                        temp_v0_2->px += 0xF00000;
                        temp_v0_2->delay = -temp_v0_2->delay;
                    }
                }
            }
            if (((u8) e->bytes[1] >= 3U) && ((u16) e->ai[1] >= 0x3CU)) {
                temp_v0_4 = e->item_state;
                if (temp_v0_4 != 0) {
                    e->item_state = temp_v0_4 - 1;
                    return;
                }
                temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                temp_a0_2 = ((temp_lo_2 + 0xE06A02E7) / MULHI_11) * 2;
                e->item_state = temp_a0_2 + 0x8C;
                if (e->bytes[1] == 3) {
                    e->item_state = temp_a0_2 + 0xB4;
                }
                temp_v0_5 = SpawnMapEntity(e, 1, 1);
                temp_lo_3 = g_rng_seed * 0x7D2B89DD;
                temp_v0_5->contents_item = 0;
                g_rng_seed = temp_lo_3 + 0xE06A02E7;
                temp_t0_2 = *((((*(void *)0x80124728 + ((temp_lo_3 + 0xE06A02E7) / 1073741824)) & 3) * 2) + ((*(void *)0x8012472C * 8) + &D_80026CFC));
                temp_v0_5->flags = (temp_v0_5->flags & 0xFFF8FFFF) | 0x30000;
                if (temp_t0_2 & 1) {
                    temp_v0_5->pz += 0x180000;
                }
                if (temp_t0_2 & 2) {
                    temp_v0_5->target_dir = 8;
                }
                temp_v0_5->delay = 0x22000;
                if (temp_v0_5->target_dir == 8) {
                    temp_v0_5->px += 0xF00000;
                    temp_v0_5->delay = -temp_v0_5->delay;
                }
            }
        } else {
            temp_v1_2 = e->bytes[2];
            *(s32 *)0x801D7F00 = (s32) temp_v1_2;
            temp_v0_6 = e->bytes[0];
            var_v1 = temp_v1_2 - temp_v0_6;
            *(s32 *)0x801D7F04 = (s32) temp_v0_6;
            if (var_v1 < 0) {
                var_v1 = 0;
            }
            *(s32 *)0x801D7F08 = var_v1;
            if (var_v1 >= *(&D_80026D40 + (e->bytes[1] * 2))) {
                *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 0x100);
            }
            e->ai[4] = 0;
            e->bytes[1] += 1;
            *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 & ~1);
        }
    }
}
