/* 8007DFC0: built-in program C70 */
extern ? D_80028198;

void AI_C70(struct Entity *e) {
    s32 temp_v1;
    s32 var_v0;
    struct Entity *temp_v0;

    if (e->holder != NULL) {
        temp_v1 = e->flags2;
        if (temp_v1 != 0) {
            if (temp_v1 == -1) {
                var_v0 = 3;
            } else {
                var_v0 = *(&D_80028198 + (temp_v1 * 4));
            }
            e->target_anim = var_v0;
            temp_v0 = e->holder;
            e->flags2 = 0;
            if (temp_v0 != NULL) {
                temp_v0->carried = NULL;
            }
            e->holder = NULL;
            e->flags = (e->flags | 0x34) & ~0x80;
            return;
        }
        e->target_anim = 0;
    }
}
