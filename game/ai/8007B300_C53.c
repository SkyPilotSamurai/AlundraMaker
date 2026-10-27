/* 8007B300: built-in program C53 */
extern ? D_80027F4C;
extern ? D_80027F64;

void AI_C53(struct Entity *e) {
    s16 temp_v0_2;
    s16 temp_v0_3;
    s16 var_v0;
    s32 temp_a1_2;
    s32 temp_v1;
    s32 var_s1;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_4;
    s32 var_v1;
    s32 var_v1_2;
    struct Entity *temp_a1;
    u8 temp_v0;
    u8 temp_v1_2;
    u8 temp_v1_3;

    temp_a1 = e->parent;
    if (temp_a1->bytes[3] != 0) {
        e->target_anim = 2;
        e->flags |= 0x40;
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* switch 1; irregular */
    case 4:                                         /* switch 1 */
        if (e->pz >= (temp_a1->pz + 0xA00000)) {
            e->fz = 0;
            e->target_anim = 5;
            temp_v1_2 = temp_a1->bytes[0];
            switch (temp_v1_2) {                    /* switch 2 */
            case 1:                                 /* switch 2 */
                e->bytes[1] = 0x1E;
                e->ai[1] = 0xF0;
                /* fallthrough */
            case 0:                                 /* switch 2 */
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                e->delay = g_ent->px;
                e->item_state = g_ent->py;
                return;
            case 2:                                 /* switch 2 */
                var_v1 = *(&D_80027F4C + (e->bytes[0] * 4));
                var_v0 = 0x3C;
block_19:
                e->ai[1] = var_v0;
                e->target_dir = var_v1;
                return;
            case 3:                                 /* switch 2 */
                var_v1_2 = 2;
block_17:
                e->target_dir = var_v1_2;
                e->ai[1] = (e->bytes[0] + 1) * 0x18;
                return;
            case 4:                                 /* switch 2 */
                var_v1_2 = 0x1E;
                goto block_17;
            case 5:                                 /* switch 2 */
                var_v1 = *(&D_80027F64 + (e->bytes[0] * 4));
                var_v0 = 0x5A;
                goto block_19;
            }
        } else {
        default:                                    /* switch 2 */
            return;
        }
        break;
    case 3:                                         /* switch 1 */
    case 5:                                         /* switch 1 */
        temp_v1_3 = temp_a1->bytes[0];
        var_s1 = e->force_adjusted != 0;
        if (temp_v1_3 != 0) {
            if (temp_v1_3 == 1) {
                temp_v0 = e->bytes[1] - 1;
                e->bytes[1] = temp_v0;
                if (!(temp_v0 & 0xFF)) {
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    e->bytes[1] = 0xA;
                }
                temp_v0_2 = (u16) e->ai[1] - 1;
                e->ai[1] = temp_v0_2;
                if (!(temp_v0_2 & 0xFFFF)) {
                    var_s1 = 1;
                }
                goto block_26;
            }
            temp_v0_3 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_3;
            if (!(temp_v0_3 & 0xFFFF)) {
                var_s1 = 1;
            }
        } else {
block_26:
            var_v0_2 = e->px - e->delay;
            temp_a1_2 = e->py - e->item_state;
            if (var_v0_2 < 0) {
                var_v0_2 = -var_v0_2;
            }
            if (var_v0_2 <= 0x100000) {
                var_v0_3 = temp_a1_2;
                if (temp_a1_2 < 0) {
                    var_v0_3 = -var_v0_3;
                }
                if (var_v0_3 <= 0x100000) {
                    var_s1 = 1;
                }
            }
        }
        if (var_s1 != 0) {
            e->target_anim = 1;
            var_v0_4 = e->flags | 0x100;
block_39:
            e->flags = var_v0_4;
        }
        break;
    case 1:                                         /* switch 1 */
        if (e->on_ground != 0) {
            e->target_anim = 2;
            var_v0_4 = e->flags | 0x40;
            goto block_39;
        }
        break;
    }
}
