/* 80074C18: built-in program C87 */
void AI_C87(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    s32 temp_v1;

    if (*(s32 *)0x801E6378 & 1) {
        e->target_anim = 1;
        e->flags |= 0x40;
        return;
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 4:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->target_anim = 2;
            e->ai[1] = 0x20;
            return;
        }
        return;
    case 2:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            play_sound(0xB6);
        }
        break;
    }
}
