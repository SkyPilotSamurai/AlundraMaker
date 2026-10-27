/* 80066A88: built-in program C96 */
void AI_C96(struct Entity *e) {
    struct Entity *temp_a0;

    temp_a0 = e->parent;
    if ((u16) temp_a0->ai[4] == 0) {
        e->flags &= ~1;
    }
    if (e->bytes[0] != 0) {
        if (e->force_adjusted != 0) {
            if ((e->sprite_index == 0x125) && ((u16) temp_a0->ai[4] != 0)) {
                e->target_dir = (e->target_dir + 0x10) & 0x1F;
                e->delay = -e->delay;
            } else {
                remove_entity(e);
            }
        }
        if (e->bytes[0] == 0) {
            goto block_9;
        }
    } else {
block_9:
        e->bytes[0] = 1;
    }
    e->pafx = e->delay;
}
