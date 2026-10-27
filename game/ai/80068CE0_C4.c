/* 80068CE0: built-in program C4 */
extern ? D_8002707C;

void AI_C4(struct Entity *e) {
    s32 temp_a0;
    s32 temp_v1;
    s32 var_v1;
    s32 var_v1_2;
    struct Entity *temp_v0;
    struct Entity *var_a0;
    struct Entity *var_a0_2;

    if (e->holder != NULL) {
        temp_v1 = e->flags2;
        if (temp_v1 != 0) {
            if (temp_v1 == -1) {
                e->target_anim = 3;
                if (e->bi_e == 2) {
                    e->flags = (e->flags | 0x10) & ~0x80;
                }
            } else {
                e->target_anim = *(&D_8002707C + (temp_v1 * 4));
            }
            temp_v0 = e->holder;
            e->flags2 = 0;
            if (temp_v0 != NULL) {
                temp_v0->carried = NULL;
            }
            e->holder = NULL;
            return;
        }
        goto block_37;
    }
    temp_a0 = e->target_anim;
    if (temp_a0 != 0) {
        if ((e->sprite_index != 0x175) || (temp_a0 != 5)) {
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
loop_25:
                if ((*var_a0_2->cell0 & 0x1001) != 0x1001) {
                    var_v1_2 += 1;
                    var_a0_2 += 4;
                    if (var_v1_2 >= 4) {

                    } else {
                        goto loop_25;
                    }
                }
                if (var_v1_2 == 4) {
                    e->target_anim = 0;
                }
            }
        }
    }
    if (e->sprite_index == 0x175) {
        switch (e->target_anim) {                   /* irregular */
        case 0:
            if (e->slope_now == 4) {
                e->target_anim = 5;
                return;
            }
            if ((e->target_anim == 5) && (e->slope_now != 4)) {
block_37:
                e->target_anim = 0;
            }
            break;
        }
    }
}
