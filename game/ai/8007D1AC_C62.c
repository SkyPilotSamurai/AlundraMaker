/* 8007D1AC: built-in program C62 */
void AI_C62(struct Entity *e) {
    s32 sp18;
    s32 sp1C;
    s32 temp_hi;
    s32 temp_lo;
    s32 temp_v1;
    s32 var_v1;
    s32 var_v1_2;
    struct Effect *temp_v0;
    struct Entity *temp_v1_3;
    struct Entity *temp_v1_4;
    struct Entity *var_a0;
    struct Entity *var_a0_2;
    u32 temp_v1_2;

    if (e->vram_and & 4) {
        remove_entity(e);
        return;
    }
    temp_v1 = e->unk274;
    e->unk274 = (s32) (temp_v1 - 1);
    if (temp_v1 != 0) {
        if ((temp_v1 < 0x3C) && !(temp_v1 & 7)) {
            temp_v0 = spawn_effect(0, 9, 0, e->px, e->py, e->pz + 0x80000);
            if (temp_v0 != NULL) {
                temp_v1_2 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                temp_lo = temp_v1_2 * 0x7D2B89DD;
                temp_hi = MULTU_HI(temp_v1_2, 0x30001);
                g_rng_seed = temp_v1_2;
                sp18 = temp_v1_2 * 0x30001;
                sp1C = temp_hi;
                g_rng_seed = temp_lo + 0xE06A02E7;
                temp_v0->vx = (temp_hi >> 0) + 0xFFFE8000;
                temp_v0->vy = ((temp_lo + 0xE06A02E7) / 32768) + 0xFFFF0000;
            }
        }
        goto block_9;
    }
    temp_v1_3 = e->holder;
    e->estatus = 3;
    if (temp_v1_3 != NULL) {
        temp_v1_3->carried = NULL;
        e->holder = NULL;
block_9:
        if (e->holder != NULL) {
            if (e->flags2 != 0) {
                temp_v1_4 = e->holder;
                e->target_anim = 2;
                e->flags2 = 0;
                if (temp_v1_4 != NULL) {
                    temp_v1_4->carried = NULL;
                }
                e->holder = NULL;
                return;
            }
            goto block_32;
        }
        goto block_14;
    }
block_14:
    if (e->target_anim != 0) {
        if (e->force_adjusted != 0) {
            var_v1 = 0;
            if (e->on_ground == 0) {
                if ((e->fz > 0) && (e->delay == 0)) {
                    e->delay = 1;
                    e->target_dir = (e->target_dir + 0x10) & 0x1F;
                    spawn_effect(0, 9, 0, e->px, e->py, e->pz + 0x80000);
                }
            } else {
                var_a0 = e;
                do {
                    if ((*var_a0->cell0 & 0x1001) == 0x1001) {
                        e->estatus = 3;
                    }
                    var_v1 += 1;
                    var_a0 += 4;
                } while (var_v1 < 4);
                e->target_anim = 0;
            }
        } else if ((e->on_ground != 0) || (e->hits != 0)) {
            play_sound(0x18);
            e->delay = 0;
            var_v1_2 = 0;
            var_a0_2 = e;
loop_28:
            if ((*var_a0_2->cell0 & 0x1001) != 0x1001) {
                var_v1_2 += 1;
                var_a0_2 += 4;
                if (var_v1_2 >= 4) {

                } else {
                    goto loop_28;
                }
            }
            if (var_v1_2 == 4) {
block_32:
                e->target_anim = 0;
            }
        }
    }
}
