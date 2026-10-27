/* 80076F78: built-in program C81 */
void AI_C81(struct Entity *e) {
    s32 temp_v0_2;
    s32 temp_v0_3;
    s32 temp_v1;
    s32 var_v0;
    u16 temp_v0;

    if (e->parent->bytes[3] == 0) {
        temp_v1 = e->target_anim;
        switch (temp_v1) {                          /* irregular */
        case 0:
            temp_v0 = (u16) e->ai[1];
            if (temp_v0 != 0) {
                e->ai[1] = temp_v0 - 1;
            }
            if (e->force_adjusted != 0) {
                temp_v0_2 = e->mpx;
                if (((temp_v0_2 + 0xFFFF0000) <= 0x780000) || ((temp_v0_2 + e->sizex + 0x10001) > 0x01F7FFFF)) {
                    var_v0 = 0x20;
                    goto block_11;
                }
                temp_v0_3 = e->mpy;
                if (((temp_v0_3 + 0xFFFF0000) <= 0xA00000) || ((temp_v0_3 + e->sizey + 0x10001) > 0x01DFFFFF)) {
                    var_v0 = 0x10;
block_11:
                    e->target_dir = (var_v0 - e->target_dir) & 0x1F;
                }
                if ((u16) e->ai[1] != 0) {
                    return;
                }
                goto block_17;
            }
            return;
        case 1:
            if (e->anim_done != 0) {
                if (e->bytes[3] != 0) {
                    goto block_17;
                }
                e->target_anim = 0;
            }
            break;
        }
    } else {
block_17:
        e->target_anim = 2;
        e->flags |= 0x40;
    }
}
