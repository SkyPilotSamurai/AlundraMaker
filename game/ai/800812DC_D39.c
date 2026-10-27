/* 800812DC: built-in program D39 */
void AI_D39(struct Entity *e) {
    struct Entity *temp_s1;

    temp_s1 = e->touching;
    if (take_hit(e) == 0) {
        if (temp_s1->sprite_index == 0x1EF) {
            goto block_3;
        }
    } else {
block_3:
        e->bytes[3] = 1;
    }
    e->target_anim = 3;
}
