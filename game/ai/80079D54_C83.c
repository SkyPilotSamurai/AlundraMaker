/* 80079D54: built-in program C83 */
void AI_C83(struct Entity *e) {
    s32 temp_v1;
    struct Entity *temp_v1_2;
    u16 temp_v0;

    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 1:
        if ((e->terrain + 1) >= e->pz) {
            e->target_anim = 2;
            e->flags = (e->flags & ~0x4000) | 0x100;
            return;
        }
        return;
    case 3:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 4;
                temp_v1_2 = e->parent;
                e->flags |= 0x40;
                temp_v1_2->ai[4] = (u16) temp_v1_2->ai[4] - 1;
                return;
            }
            if (e->collided_z != 0) {
                e->target_anim = 0;
                return;
            }
block_16:
            e->target_anim = 1;
        }
        break;
    case 5:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        goto block_16;
    }
}
