/* 8008133C: built-in program D40 */
void AI_D40(struct Entity *e) {
    struct Entity *temp_a0;
    u8 temp_v1;

    if (e->sprite_index == 0x1D7) {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 2;
        e->ai[4] = 1;
        return;
    }
    temp_a0 = e->parent;
    e->target_anim = 2;
    temp_v1 = temp_a0->bytes[0];
    if (temp_v1 < 0x60U) {
        temp_a0->bytes[0] = temp_v1 + 0x20;
        temp_a0->bytes[1] = 0x10;
        if ((u8) temp_a0->bytes[0] >= 0x61U) {
            temp_a0->bytes[0] = 0x60;
        }
    }
}
