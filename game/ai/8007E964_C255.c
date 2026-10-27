/* 8007E964: built-in program C255 */
? func_80033240(struct Entity *);                   /* extern */
? func_800344D4(struct Entity *, s32);              /* extern */
s32 func_80034614(struct Entity *, s32);            /* extern */
? func_8003B67C(struct Entity *);                   /* extern */
? func_8003B6F4(struct Entity *);                   /* extern */
s32 func_80045F8C(s32);                             /* extern */
? func_8004600C(?);                                 /* extern */
? func_8004608C(void *, ?);                         /* extern */
? func_8004AC90();                                  /* extern */
? func_8004AD18(?);                                 /* extern */
s32 func_8005C990(s32);                             /* extern */
? func_8005CB94(?);                                 /* extern */
s32 func_80083FC4(?);                               /* extern */
? func_800846E8(?, s32);                            /* extern */
? func_800847F4(?, s32);                            /* extern */
extern s32 D_80029B70;
extern s32 D_8009C6C0;
extern ? D_800C7DE4;
extern ? D_800C7DE9;

void AI_C255(struct Entity *e) {
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a1;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_s0;
    s32 temp_s3;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 var_a0;
    s32 var_v0;
    struct Entity *var_a0_2;
    u8 temp_s0_2;
    u8 temp_s0_3;

    var_a0 = e->unk274;
    temp_s3 = e->sprite_index - 0x1E;
    if (var_a0 == 2) {
        temp_v0 = e->delay;
        if (temp_v0 == 0) {
            temp_v1 = e->item_state;
            switch (temp_v1) {                      /* switch 1; irregular */
            default:                                /* switch 1 */
                if (temp_v1 != var_a0) {
                    return;
                }
                if (func_80045F8C(var_a0) == 0) {
                    if (e->unk284 != 0) {
                        func_800344D4(g_ent, temp_s3);
                        func_80033240(e->unk280->contents_flag);
                    } else {
                        e->unk280->target_anim = 0;
                    }
                    var_a0_2 = e->unk280;
                    goto block_72;
                }
                break;
            case 0:                                 /* switch 1 */
                e->fz = 0;
                if (func_80045F8C(var_a0) == 0) {
                    if (e->unk284 != 0) {
                        func_800847F4(0x80124858, func_80083FC4(0x4C));
                        temp_s0 = temp_s3 * 8;
                        func_800846E8(0x80124858, *(&D_800C7DE4 + temp_s0));
                        func_800846E8(0x80124858, func_80083FC4(0x4D));
                        if (e->unk288 != 0) {
                            e->item_state += 1;
                            goto block_62;
                        }
                        e->item_state += 2;
                        temp_s0_2 = *(&D_800C7DE9 + temp_s0);
                        if (temp_s0_2 == 0) {
                            func_800846E8(0x80124858, func_80083FC4(0x46));
                        }
                        play_sound((s32) temp_s0_2);
                        goto block_16;
                    }
                    e->item_state += 2;
                    func_800847F4(0x80124858, func_80083FC4(0x4E));
                    func_800846E8(0x80124858, *(&D_800C7DE4 + (temp_s3 * 8)));
                    func_800846E8(0x80124858, func_80083FC4(0x4F));
block_16:
                    func_8004608C((void *)0x80124858, 1);
                    return;
                }
                break;
            }
        } else {
            e->delay = temp_v0 - 1;
        }
    } else {
        if (e->on_ground != 0) {
            temp_v1_2 = e->unk284;
            if (temp_v1_2 != 0) {
                temp_v0_2 = (s32) (temp_v1_2 * 0xC) >> 4;
                e->unk284 = temp_v0_2;
                if ((g_tile_effects_addr->unk4 << 8) >= temp_v0_2) {
                    e->unk284 = 0;
                }
                e->fz = e->unk284;
            }
        }
        temp_v1_3 = e->delay;
        temp_v1_4 = temp_v1_3 - 1;
        if ((u32) (temp_v1_3 + 1) >= 2U) {
            e->delay = temp_v1_4;
            if (temp_v1_4 != 0) {
                if (temp_v1_4 == 0x78) {
                    e->damaged_tick = temp_v1_4;
                }
                goto block_32;
            }
            goto block_73;
        }
block_32:
        temp_v1_5 = e->item_state;
        var_a0 = 1;
        switch (temp_v1_5) {                        /* switch 2; irregular */
        case 0:                                     /* switch 2 */
            if (e->fz <= 0) {
                e->item_state = 1;
                return;
            }
            return;
        case 1:                                     /* switch 2 */
            if (func_80045F8C(1) == 0) {
                temp_a1 = e->mpx;
                temp_a0 = temp_a1 - g_ent->mpx;
                if (temp_a0 >= 0) {
                    if (temp_a0 < (g_ent->sizex + 1)) {
                        goto block_46;
                    }
                } else if ((g_ent->mpx - temp_a1) < (e->sizex + 1)) {
block_46:
                    temp_a1_2 = e->mpy;
                    temp_a0_2 = temp_a1_2 - g_ent->mpy;
                    if (temp_a0_2 >= 0) {
                        if (temp_a0_2 < (g_ent->sizey + 1)) {
                            goto block_50;
                        }
                    } else if ((g_ent->mpy - temp_a1_2) < (e->sizey + 1)) {
block_50:
                        temp_a1_3 = e->mpz;
                        temp_a0_3 = temp_a1_3 - g_ent->mpz;
                        if (temp_a0_3 >= 0) {
                            if (temp_a0_3 < (g_ent->sizez + 1)) {
                                goto block_54;
                            }
                        } else if ((g_ent->mpz - temp_a1_3) < (e->sizez + 1)) {
block_54:
                            var_v0 = temp_s3 * 8;
                            if ((func_80034614(g_ent, temp_s3) != 0) || (var_v0 = temp_s3 * 8, (e->unk274 == 0))) {
                                func_800847F4(0x80124858, *(&D_800C7DE4 + var_v0));
                                func_800846E8(0x80124858, func_80083FC4(0x45));
                            } else {
                                *(u8 *)0x80124858 = 0;
                            }
                            func_80033240(e->unk280);
                            temp_s0_3 = *(&D_800C7DE9 + (temp_s3 * 8));
                            if (temp_s0_3 == 0) {
                                if ((D_80029B70 != 0) || (D_8009C6C0 != 0)) {
                                    e->item_state = e->item_state + 1;
                                    func_8003B67C(e);
                                    func_8004AD18(0);
                                    func_8005CB94(0xB);
                                    if (*(void *)0x80124858 != 0) {
block_62:
                                        func_8004608C((void *)0x80124858, 1);
                                    }
                                    func_8004600C(4);
                                    return;
                                }
                                func_800846E8(0x80124858, func_80083FC4(0x46));
                                goto block_66;
                            }
                            play_sound((s32) temp_s0_3);
block_66:
                            if (*(void *)0x80124858 != 0) {
                                func_8004608C((void *)0x80124858, 0);
                            }
                            e->item_state += 2;
                            return;
                        }
                    }
                }
            }
            break;
        case 2:                                     /* switch 2 */
        case 1:                                     /* switch 1 */
            if (func_8005C990(var_a0) == 0) {
                e->item_state += 1;
                func_8004600C(3);
                func_8004AC90();
                return;
            }
            break;
        case 3:                                     /* switch 2 */
            var_a0_2 = e;
            if (func_80045F8C(1) == 0) {
block_72:
                func_8003B6F4(var_a0_2);
block_73:
                remove_entity(e);
            }
            break;
        }
    }
}
