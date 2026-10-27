/* 8007C16C: built-in program C86 */
extern ? D_800282D8;
extern ? D_800286D8;

void AI_C86(struct Entity *e) {
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 var_a3;
    s32 var_t0;
    struct Entity *temp_a2;
    void *temp_v0;
    void *temp_v1;

    temp_a2 = e->parent;
    if (e->target_anim != 2) {
        if (temp_a2->bytes[3] == 0) {
            temp_v1 = temp_a2->unk284;
            if (temp_v1 != NULL) {
                if (temp_v1->unk118 <= 0x01DFFFFF) {
                    goto block_4;
                }
                goto block_16;
            }
            goto block_5;
        }
        goto block_16;
    }
block_4:
    temp_v0 = temp_a2->unk284;
    if (temp_v0 == NULL) {
block_5:
        var_a3 = temp_a2->px;
        var_t0 = temp_a2->py;
    } else {
        var_a3 = temp_v0->unk114;
        var_t0 = temp_v0->unk118;
    }
    temp_v1_2 = ((temp_a2->delay + e->delay) & 0x1FF) * 2;
    e->px = var_a3 + (*(&D_800282D8 + temp_v1_2) * (temp_a2->item_state + 0x1000));
    temp_v1_3 = e->target_anim;
    e->py = var_t0 - (*(&D_800286D8 + temp_v1_2) * (temp_a2->item_state + 0x1000));
    switch (temp_v1_3) {                            /* irregular */
    case 1:
        if (e->anim_done != 0) {
block_13:
            e->target_anim = 0;
            return;
        }
        return;
    case 3:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
block_16:
                e->target_anim = 2;
                return;
            }
            goto block_13;
        }
        break;
    case 2:
        if (e->anim_done != 0) {
            temp_a2->ai[4] = (u16) temp_a2->ai[4] - 1;
            destroy_entity(e, -1);
        }
        break;
    }
}
