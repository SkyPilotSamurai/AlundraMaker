/* 8007CB30: built-in program C56 */
? func_8007C2EC(struct Effect *);                   /* extern */

void AI_C56(struct Entity *e) {
    s32 temp_v0;
    s32 var_v0;
    struct Entity *temp_a0;
    u16 temp_v0_2;
    u8 var_v1;

    func_8007C2EC(e->unk284);
    temp_a0 = e->parent;
    if (temp_a0->target_anim != 7) {
        temp_v0 = e->target_anim;
        switch (temp_v0) {
        case 14:
            temp_v0_2 = (u16) e->ai[1];
            if (temp_v0_2 != 0) {
                e->ai[1] = temp_v0_2 - 1;
                return;
            }
            if (e->bytes[0] != 0) {
                play_sound(0x12A);
                e->unk284 = spawn_effect(1, 0, 0, e->px, e->py, e->pz);
                e->bytes[0] = 0;
                return;
            }
            var_v1 = e->unk284->b70;
            var_v0 = 1;
block_17:
            if (var_v1 == var_v0) {
                e->target_anim = (s32) var_v1;
                return;
            }
        default:
            return;
        case 1:
            if (e->anim_done != 0) {
                if (temp_a0->bytes[1] == 0) {
                    e->target_anim = 4;
                    return;
                }
                e->target_anim = 3;
                return;
            }
            break;
        case 3:
            if (temp_a0->target_anim == 2) {
                goto block_20;
            }
            break;
        case 4:
            if (e->anim_done != 0) {
                e->target_anim = 5;
                return;
            }
            break;
        case 5:
            var_v1 = (u8) temp_a0->target_anim;
            var_v0 = 6;
            goto block_17;
        case 6:
            if (e->anim_done != 0) {
                goto block_20;
            }
            break;
        case 13:
            if (e->anim_done != 0) {
                e->flags |= 0x40;
                e->unk284->b70 = 2;
                e->unk284 = NULL;
            }
            break;
        }
    } else {
block_20:
        e->target_anim = 0xD;
    }
}
