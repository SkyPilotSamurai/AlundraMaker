/* 80081CDC: built-in program E17 */
void AI_E17(struct Entity *e) {
    s32 *var_a0;
    s32 temp_a3;
    s32 temp_t0;
    s32 temp_t1;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 var_a1;
    s32 var_a2;
    s32 var_t5;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v0_3;

    temp_v1 = e->target_anim;
    if (temp_v1 == 1) {
        if (e->anim_done == temp_v1) {
            destroy_entity(e, -1);
        }
    } else {
        if (e->hits != 0) {
            temp_v1_2 = e->flags;
            temp_t1 = e->atk_x;
            temp_t0 = e->atk_y;
            temp_a3 = e->atk_z;
            var_a1 = (temp_v1_2 * 4) & 8;
            if (temp_v1_2 & 4) {
                var_a1 |= 1;
            }
            if (temp_v1_2 & 0x1000) {
                var_a1 |= 0x800;
            }
            var_t5 = 1;
            if (var_a1 != 0) {
                var_a2 = 0;
                if (g_ent_count >= 0) {
                    var_a0 = &g_ent->sprite_index;
loop_12:
                    if ((&e->sprite_index != var_a0) && !(var_a0->unk4C & 0x40) && (var_a0->unk164 == 0) && (var_a0->unk4 & var_a1)) {
                        temp_v0 = var_a0->unk170;
                        temp_v1_3 = temp_t1 - temp_v0;
                        if (temp_v1_3 >= 0) {
                            var_v0 = temp_v1_3 < (var_a0->unk188 + 1);
                        } else {
                            var_v0 = (temp_v0 - temp_t1) < (e->atk_w + 1);
                        }
                        if (var_v0 != 0) {
                            temp_v0_2 = var_a0->unk174;
                            temp_v1_4 = temp_t0 - temp_v0_2;
                            if (temp_v1_4 >= 0) {
                                var_v0_2 = temp_v1_4 < (var_a0->unk18C + 1);
                            } else {
                                var_v0_2 = (temp_v0_2 - temp_t0) < (e->atk_h + 1);
                            }
                            if (var_v0_2 != 0) {
                                temp_v0_3 = var_a0->unk178;
                                temp_v1_5 = temp_a3 - temp_v0_3;
                                if (temp_v1_5 >= 0) {
                                    var_v0_3 = temp_v1_5 < (var_a0->unk190 + 1);
                                } else {
                                    var_v0_3 = (temp_v0_3 - temp_a3) < (e->atk_d + 1);
                                }
                                if ((var_v0_3 == 0) || (var_a0->unk0 == 0x1AD)) {
                                    goto block_29;
                                }
                                var_t5 = 0;
                            } else {
                                goto block_29;
                            }
                        } else {
                            goto block_29;
                        }
                    } else {
block_29:
                        var_a2 += 1;
                        var_a0 += 0x294;
                        if (g_ent_count >= var_a2) {
                            goto loop_12;
                        }
                    }
                }
                if (var_t5 != 0) {
                    e->estatus = 2;
                    return;
                }
                goto block_32;
            }
block_32:
            destroy_entity(e, -1);
            goto block_33;
        }
block_33:
        e->target_anim = 1;
        e->target_dir = (e->target_dir + 0x10) & 0x1F;
        e->flags = (e->flags | 0x140) & ~0x30;
    }
}
