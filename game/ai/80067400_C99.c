/* 80067400: built-in program C99 */
void AI_C99(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    s32 temp_v1;

    if (!(*(s32 *)0x801E6378 & 1) && (e->target_anim != 0x10)) {
        e->target_anim = 0x10;
        return;
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 17:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 0x12;
            e->ai[1] = (s16) (u16) e->ai[4];
            return;
        }
        return;
    case 18:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            return;
        }
        break;
    case 0:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            e->target_anim = 0x10;
            return;
        }
        break;
    case 16:
        if (e->anim_done != 0) {
            remove_entity(e);
        }
        break;
    }
}
