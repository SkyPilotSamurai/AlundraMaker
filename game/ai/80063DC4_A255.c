/* 80063DC4: built-in program A255 */
? func_8005CB94(?, struct Entity *);                /* extern */

void AI_A255(struct Entity *e) {
    s32 *var_a0;
    s32 temp_a0;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 var_v0;

    if (e->sprite_index == 0x1E) {
        if (e->contents_item == 0) {
            e->target_anim = 1;
        }
    } else {
        temp_v1 = e->unk274;
        if (temp_v1 != 1) {
            if (temp_v1 == 2) {
                if (e->unk280->unk88 != 1) {
                    e->estatus = 1;
                    return;
                }
                if (e->unk288 != 0) {
                    func_8005CB94(0xB, e);
                }
            } else {
                temp_a0 = e->contents_flag;
                e->flags &= ~0x80;
                if (temp_a0 != 0) {
                    temp_v1_2 = ((u32) temp_a0 >> 3) & 0xFFC;
                    if (temp_a0 & 0x8000) {
                        var_a0 = temp_v1_2 + 0x801E6378;
                    } else {
                        var_a0 = temp_v1_2 + 0x801DD334;
                    }
                    temp_v1_3 = e->contents_flag;
                    var_v0 = temp_v1_3;
                    if (temp_v1_3 < 0) {
                        var_v0 = temp_v1_3 + 0x1F;
                    }
                    if (!(*var_a0 & (1 << (temp_v1_3 - ((var_v0 >> 5) << 5))))) {
                        remove_entity(e);
                        return;
                    }
                    goto block_17;
                }
block_17:
                e->item_state = 0;
                e->unk280 = (void *)-1;
                e->unk284 = 0;
                e->delay = e->contents_flag;
            }
        }
    }
}
