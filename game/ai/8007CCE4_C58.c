/* 8007CCE4: built-in program C58 */
extern ? D_800282D8;
extern ? D_800286D8;

void AI_C58(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    s32 temp_v1;
    s32 temp_v1_2;
    struct Entity *temp_s1;

    temp_s1 = e->parent;
    if (temp_s1->bytes[3] != 0) {
        e->target_anim = 3;
        e->flags |= 0x40;
        return;
    }
    if ((u32) (e->target_anim - 1) < 2U) {
        temp_v0 = (u16) e->ai[1] + 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 3)) {
            spawn_effect(1, 1, 0, e->px, e->py, e->pz);
        }
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 1:
        temp_v1_2 = e->delay;
        if (temp_v1_2 < 0x1800) {
            e->delay = temp_v1_2 + 0x40;
        } else {
            e->item_state -= 8;
        }
        temp_v0_2 = ((u16) e->ai[4] + 0xA) & 0x1FF;
        e->ai[4] = temp_v0_2;
        e->px = (*(&D_800282D8 + (temp_v0_2 * 2)) * e->delay) + 0x01500000;
        e->py = (*(&D_800286D8 + ((u16) e->ai[4] * 2)) * e->delay) + 0x03100000;
        if (e->item_state == 0) {
            play_sound(0x127);
            e->target_anim = 2;
            e->target_dir = (0x20 - ((u16) e->ai[4] >> 4)) & 0x1F;
            return;
        }
        return;
    case 2:
        if (e->force_adjusted != 0) {
            e->target_anim = 3;
            e->flags |= 0x40;
            temp_s1->ai[4] = (u16) temp_s1->ai[4] - 1;
        }
        break;
    }
}
