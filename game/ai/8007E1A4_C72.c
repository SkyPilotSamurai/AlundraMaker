/* 8007E1A4: built-in program C72 */
? func_80031AC4();                                  /* extern */
s32 func_80045F8C();                                /* extern */
? func_80045FE4();                                  /* extern */
? func_8004600C(?);                                 /* extern */
? func_8004608C(s32, ?);                            /* extern */
s32 func_80052310(s32, s32, ?);                     /* extern */
s32 func_80083FC4(?);                               /* extern */

void AI_C72(struct Entity *e) {
    s32 temp_s0;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v1;
    s32 var_v0;

    temp_v1 = e->unk274;
    switch (temp_v1) {                              /* irregular */
    case 1:
        if (func_80045F8C() == 0) {
            func_8004608C(func_80083FC4(0x40), 1);
            func_8004600C(4);
block_15:
            e->delay = 0x3C;
            var_v0 = e->unk274 + 1;
block_16:
            e->unk274 = var_v0;
            return;
        }
block_19:
        e->unk274 = 0;
        g_mode_flags &= ~4;
        return;
    case 2:
        temp_v0 = e->delay - 1;
        e->delay = temp_v0;
        if (temp_v0 == -1) {
            *(void *)0x80124854 = 0;
            temp_s0 = func_80083FC4(0x41);
            if (func_80052310(temp_s0, func_80083FC4(0x42), 0x80124854) != 0) {
                e->unk274 = (s32) (e->unk274 + 1);
            }
            var_v0 = e->unk274 + 1;
            goto block_16;
        }
        break;
    case 4:
        if (*(s32 *)0x80124854 != 0) {
            func_80045FE4();
            if (*(void *)0x80124854 == 1) {
                goto block_15;
            }
            goto block_19;
        }
        break;
    case 5:
        temp_v0_2 = e->delay - 1;
        e->delay = temp_v0_2;
        if (temp_v0_2 == -1) {
            func_80031AC4();
            goto block_19;
        }
        break;
    }
}
