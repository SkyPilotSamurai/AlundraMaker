/* 80070D14: built-in program C36 */
void AI_C36(struct Entity *e) {
    u16 temp_v0;
    u8 temp_a1;

    if ((e->target_anim == 0) && (temp_a1 = e->bytes[0], ((temp_a1 & 0xFF) != 0x40))) {
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        e->bytes[0] = temp_a1 + 1;
        e->ai[1] = 4;
        e->target_dir = (e->target_dir + 1) & 0x1F;
    }
}
