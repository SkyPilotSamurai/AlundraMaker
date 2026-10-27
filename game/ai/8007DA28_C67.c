/* 8007DA28: built-in program C67 */
extern ? D_800282D8;
extern s16 D_800285D8;
extern ? D_800286D8;
extern s16 D_800289D8;

void AI_C67(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    u8 temp_a1;
    u8 temp_v1;

    temp_v1 = e->bytes[0];
    switch (temp_v1) {                              /* irregular */
    case 0:
        e->bytes[0] = 1;
        e->ai[1] = 0x180;
        e->delay = e->px - (D_800285D8 * 0xC00);
        e->item_state = e->py - (D_800289D8 * 0xC00);
        /* fallthrough */
    case 1:
        temp_v0 = ((u16) e->ai[1] + 4) & 0x1FF;
        e->ai[1] = temp_v0;
        e->px = e->delay + (*(&D_800282D8 + (temp_v0 * 2)) * 0xC00);
        e->py = e->item_state + (*(&D_800286D8 + ((u16) e->ai[1] * 2)) * 0xC00);
        if (select(e, e->ref_id - 1) == 0) {
            e->bytes[1] = 4;
            e->bytes[0] += 1;
            return;
        }
        return;
    case 2:
        temp_v0_2 = ((u16) e->ai[1] + 4) & 0x1FF;
        temp_a1 = e->bytes[1] - 1;
        e->bytes[1] = temp_a1;
        e->ai[1] = temp_v0_2;
        e->px = e->delay + (*(&D_800282D8 + (temp_v0_2 * 2)) * 0xC00);
        e->py = e->item_state + (*(&D_800286D8 + ((u16) e->ai[1] * 2)) * 0xC00);
        if (!(temp_a1 & 0xFF)) {
            e->estatus = 3;
            play_sound(0xE1);
        }
        break;
    }
}
