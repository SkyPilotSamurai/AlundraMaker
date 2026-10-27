/* 8007CEB0: built-in program C59 */
void AI_C59(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    s16 temp_v0_4;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 var_v0_2;
    struct Entity *temp_a0;
    u16 temp_v0_3;
    u32 var_v0;
    u8 temp_a0_2;

    temp_a0 = e->parent;
    if (temp_a0->bytes[3] != 0) {
        e->target_anim = 2;
        e->flags |= 0x40;
        return;
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {
    case 0:
        temp_v0 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0;
        if (!(temp_v0 & 0xFFFF)) {
            e->ai[1] = 0x28;
block_8:
            e->target_anim = (s32) e->bytes[0];
            return;
        }
    default:
        return;
    case 1:
        temp_v0_2 = (u16) e->ai[1] - 1;
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 0xFFFF)) {
            e->ai[1] = 0x14;
            goto block_8;
        }
        break;
    case 4:
    case 5:
    case 6:
    case 7:
        temp_v0_3 = (u16) e->ai[1];
        temp_v0_4 = temp_v0_3 - 1;
        if (temp_v0_3 != 0) {
            e->ai[1] = temp_v0_4;
            if (!(temp_v0_4 & 0xFFFF)) {
                temp_v1_2 = e->target_dir - dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                if ((temp_v1_2 >= 0x10) || (var_v0 = temp_v1_2 - 1, (((u32) (temp_v1_2 + 0x10) < 0x10U) != 0))) {
                    e->bytes[1] = 1;
                    var_v0 = temp_v1_2 - 1;
                }
                if ((var_v0 < 0xFU) || (temp_v1_2 < -0x10)) {
                    e->bytes[1] = 0xFF;
                }
                var_v0_2 = temp_v1_2;
                if (temp_v1_2 < 0) {
                    var_v0_2 = -var_v0_2;
                }
                if (var_v0_2 >= 8) {
                    e->bytes[1] *= 2;
                }
                e->target_dir = (e->target_dir + e->bytes[1]) & 0x1F;
                e->ai[1] = 0x12 - ((e->target_anim - 4) * 4);
                return;
            }
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->target_anim = 2;
                e->flags |= 0x40;
                temp_a0->bytes[2] -= 1;
                return;
            }
            temp_a0_2 = e->bytes[0];
            e->ai[1] = 0x1E;
            e->target_anim = 0;
            if ((temp_a0_2 & 0xFF) != 7) {
                e->bytes[0] = temp_a0_2 + 1;
            }
        }
        break;
    }
}
