/* 80075CFC: built-in program C85 */
void AI_C85(struct Entity *e) {
    s16 temp_v0_2;
    s32 temp_v1;
    s32 temp_v1_2;
    struct Entity *temp_v0;

    temp_v0 = e->parent;
    e->py = temp_v0->py;
    temp_v1 = temp_v0->target_anim;
    if ((temp_v1 == 9) || (temp_v1 == 6)) {
        e->target_anim = 2;
        e->flags |= 0x40;
    }
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {                            /* irregular */
    case 1:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            e->ai[1] = 0xB4;
            return;
        }
        return;
    case 0:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            e->target_anim = 2;
            e->flags |= 0x40;
        }
        break;
    }
}
