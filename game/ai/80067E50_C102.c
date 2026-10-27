/* 80067E50: built-in program C102 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
void AI_C102(struct Entity *e) {
    s16 temp_v0_2;
    s16 temp_v0_5;
    s16 var_v0;
    s16 var_v0_2;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_s1;
    s32 var_s1_2;
    s32 var_s2;
    s32 var_s2_2;
    struct Entity *temp_v0_3;
    struct Entity *temp_v0_6;
    u16 temp_v0;
    u16 temp_v0_4;
    u32 var_v0_3;

    if (e->bytes[0] == 0) {
        e->ai[1] = 0x3C;
        e->bytes[0] = 1;
    }
    if (e->sprite_index == 0x1CB) {
        temp_v1 = e->target_anim;
        switch (temp_v1) {                          /* switch 1; irregular */
        case 0:                                     /* switch 1 */
            temp_v0 = (u16) e->ai[1];
            var_v0 = temp_v0 - 1;
            if (temp_v0 == 0) {
                start_moving(e, 1, 0x3C, 0x64);
                return;
            }
            goto block_33;
        case 1:                                     /* switch 1 */
            temp_v0_2 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_2;
            var_v0_2 = 0x3C;
            if (temp_v0_2 & 0xFFFF) {
                if (e->force_adjusted != 0) {
                    var_v0_3 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                    goto block_38;
                }
            } else {
                goto block_43;
            }
            break;
        case 3:                                     /* switch 1 */
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    e->target_anim = 6;
                    return;
                }
                goto block_42;
            }
            break;
        case 6:                                     /* switch 1 */
            if (e->anim_done != 0) {
                var_s1 = 0;
                if (e->bytes[1] == 0) {
                    var_s2 = 4;
                    do {
                        temp_v0_3 = SpawnMapEntity(e, 0x24, 1);
                        if (temp_v0_3 != NULL) {
                            temp_v0_3->target_anim = 1;
                            temp_v0_3->px = e->px;
                            temp_v0_3->py = e->py;
                            temp_v0_3->target_dir = var_s2;
                            temp_v0_3->ai[1] = 0x3C;
                            temp_v0_3->pz = e->pz;
                        }
                        var_s1 += 1;
                        var_s2 += 8;
                    } while (var_s1 != 4);
                    goto block_52;
                }
                goto block_46;
            }
            break;
        }
    } else {
        temp_v1_2 = e->target_anim;
        switch (temp_v1_2) {                        /* switch 2; irregular */
        case 0:                                     /* switch 2 */
            temp_v0_4 = (u16) e->ai[1];
            var_v0 = temp_v0_4 - 1;
            if (temp_v0_4 != 0) {
block_33:
                e->ai[1] = var_v0;
                return;
            }
            start_moving(e, 1, 0x3C, 0x14);
            return;
        case 1:                                     /* switch 2 */
            temp_v0_5 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_5;
            var_v0_2 = 0x3C;
            if (temp_v0_5 & 0xFFFF) {
                if (e->force_adjusted != 0) {
                    var_v0_3 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
block_38:
                    g_rng_seed = var_v0_3;
                    e->target_dir = (e->target_dir + ((var_v0_3 / MULHI_5) - 0x14)) & 0x1F;
                    return;
                }
                return;
            }
block_43:
            e->target_anim = 0;
            e->ai[1] = var_v0_2;
            return;
        case 2:                                     /* switch 2 */
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    e->target_anim = 3;
                    return;
                }
block_42:
                e->damaged_tick = 0x5A;
                var_v0_2 = 0x28;
                goto block_43;
            }
            break;
        case 3:                                     /* switch 2 */
            if (e->anim_done != 0) {
                var_s1_2 = 0;
                if (e->bytes[1] != 0) {
block_46:
                    remove_entity(e);
                    return;
                }
                var_s2_2 = 4;
                do {
                    temp_v0_6 = SpawnMapEntity(e, 0x25, 1);
                    if (temp_v0_6 != NULL) {
                        temp_v0_6->target_anim = 0x13;
                        temp_v0_6->px = e->px;
                        temp_v0_6->py = e->py;
                        temp_v0_6->target_dir = var_s2_2;
                        temp_v0_6->bi_a = 0;
                        temp_v0_6->ai[1] = 0x1E;
                        temp_v0_6->pz = e->pz;
                    }
                    var_s1_2 += 1;
                    var_s2_2 += 8;
                } while (var_s1_2 != 4);
block_52:
                e->bytes[1] = 1;
            }
            break;
        }
    }
}
