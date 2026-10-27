/* 80067088: built-in program C98 */
extern ? D_80026E0C;
extern ? D_80026E18;
extern ? D_80026E1A;
extern ? D_80026E28;
extern ? D_80026EF0;
extern ? D_80026EF8;
extern ? D_80026F1C;
extern ? D_80026F40;
extern ? D_80026F70;

void AI_C98(struct Entity *e) {
    ? *var_s1;
    s16 temp_v0;
    s16 var_a1_2;
    s16 var_s3;
    s32 temp_a0_2;
    s32 temp_v0_2;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_a0;
    s32 var_a1;
    s32 var_v0;
    struct Entity *temp_v0_3;
    struct Entity *var_v1;
    u16 *var_s1_2;
    u16 temp_a0_3;
    u16 temp_v1_4;
    u32 temp_a0;
    u32 temp_v1_3;
    void *var_s0;

    temp_v1 = *(s32 *)0x801E6378;
    if (temp_v1 & 1) {
        if ((u16) e->ai[4] == 0) {
            if (temp_v1 & 0x80) {
                e->bytes[1] = 0;
                *(s32 *)0x801E6378 &= ~0x80;
            }
            e->bytes[2] = 0;
            e->item_state = 0;
            e->ai[1] = 0;
            *(void **)0x80124738 = (e->bytes[1] * 0x28) + &D_80026E28;
            *(s32 *)0x801E6378 &= ~0x100;
            e->ai[4] = 1;
        }
        temp_v0 = (u16) e->ai[1] + 1;
        e->ai[1] = temp_v0;
        if ((u32) (temp_v0 & 0xFFFF) >= 0x708U) {
            *(s32 *)0x801D7F00 = (s32) e->bytes[2];
            if ((s32) e->bytes[2] >= *(&D_80026E0C + (e->bytes[1] * 2))) {
                *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 | 0x100);
            }
            e->ai[4] = 0;
            e->bytes[1] += 1;
            *(void *)0x801E6378 = (s32) (*(void *)0x801E6378 & ~1);
            return;
        }
        var_v1 = g_ent;
        var_a0 = 0;
        if (g_ent_count >= 0) {
loop_10:
            var_a0 += 1;
            if ((u32) (var_v1->ref_id - 4) >= 9U) {
                var_v1 += 0x294;
                if (g_ent_count < var_a0) {
                    goto block_12;
                }
                goto loop_10;
            }
        } else {
block_12:
            temp_v0_2 = e->delay;
            var_v0 = temp_v0_2 - 1;
            if (temp_v0_2 == 0) {
                temp_v1_2 = e->item_state;
                var_s3 = *((temp_v1_2 * 2) + *(void *)0x80124738);
                e->item_state = temp_v1_2 + 1;
                switch (var_s3) {
                case 1:
                    var_s1 = &D_80026EF0;
                    var_a1 = 0;
block_21:
                    temp_a0 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                    g_rng_seed = temp_a0;
                    var_s1_2 = var_s1 + (var_s3 * ((s32) MULTU_HI(temp_a0, (var_a1 + 1)) >> 0) * 6);
                    if (var_s3 != 0) {
                        var_s0 = var_s1_2 + 4;
                        do {
                            var_a1_2 = var_s0->unk-2;
                            if (var_a1_2 & 0x80) {
                                temp_a0_2 = (var_a1_2 & 0xF) * 4;
                                temp_v1_3 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                                g_rng_seed = temp_v1_3;
                                var_a1_2 = *(&D_80026E1A + temp_a0_2) + ((s32) MULTU_HI(temp_v1_3, (*(&D_80026E18 + temp_a0_2) + 1)) >> 0);
                            }
                            temp_v0_3 = SpawnMapEntity(e, (s32) var_a1_2, 1);
                            temp_a0_3 = var_s0->unk0;
                            var_s0 += 6;
                            temp_v1_4 = *var_s1_2;
                            var_s1_2 += 6;
                            var_s3 -= 1;
                            temp_v0_3->contents_item = 0;
                            temp_v0_3->ai[1] = (s16) temp_v1_4;
                            temp_v0_3->ai[4] = (s16) temp_a0_3;
                        } while (var_s3 != 0);
                    }
                    var_v0 = 0x14;
                    goto block_27;
                case 2:
                    var_s1 = &D_80026EF8;
                    var_a1 = 2;
                    goto block_21;
                case 3:
                    var_s1 = &D_80026F1C;
                    var_a1 = 1;
                    goto block_21;
                case 4:
                    var_s1 = &D_80026F40;
                    var_a1 = 1;
                    goto block_21;
                case 6:
                    var_s1 = &D_80026F70;
                    var_a1 = 1;
                    goto block_21;
                default:
                    e->item_state -= 1;
                    return;
                }
            } else {
block_27:
                e->delay = var_v0;
            }
        }
    }
}
