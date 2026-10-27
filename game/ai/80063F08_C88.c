/* 80063F08: built-in program C88 */
? func_80083394();                                  /* extern */

void AI_C88(struct Entity *e) {
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v0_4;
    s32 temp_v0_5;
    struct Entity *temp_v0_3;
    struct Entity *temp_v0_6;
    u8 temp_v1;

    temp_v1 = e->bytes[3];
    if (temp_v1 != 0) {
        if (e->target_anim == 0) {
            if (temp_v1 < 2U) {
                func_80083394();
                return;
            }
            *(s32 *)0x801E6378 |= 1;
            return;
        }
        goto block_12;
    }
    if (e->target_anim == 0) {
        temp_v0 = e->delay;
        temp_v0_2 = temp_v0 - 1;
        if (temp_v0 != 0) {
            e->delay = temp_v0_2;
            if (temp_v0_2 == 0) {
                temp_v0_3 = spawn_warp_entity(e, 1, 0xD0, 0xF00000, /* extra? */ 0xA00000, /* extra? */ 0, /* extra? */ 0);
                temp_v0_3->bytes[0] = 0;
                temp_v0_3->bytes[1] = 0;
                temp_v0_3->target_anim = 8;
            }
        }
        temp_v0_4 = e->item_state;
        temp_v0_5 = temp_v0_4 - 1;
        if (temp_v0_4 != 0) {
            e->item_state = temp_v0_5;
            if (temp_v0_5 == 0) {
                temp_v0_6 = spawn_warp_entity(e, 1, 0xD0, 0xF00000, /* extra? */ 0xA00000, /* extra? */ 0, /* extra? */ 8);
                temp_v0_6->bytes[0] = 1;
                temp_v0_6->bytes[1] = 0;
                temp_v0_6->target_anim = 8;
            }
        }
    } else {
block_12:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                play_sound(0x55);
                *(s32 *)0x801F94D0 = 1;
                *(s32 *)0x801F94DC = 1;
                *(s32 *)0x801F94E0 = 1;
                *(s32 *)0x801F94D4 = 2;
                *(s32 *)0x801F94D8 = 2;
                return;
            }
            e->target_anim = 0;
            e->damaged_tick = 0x5A;
        }
    }
}
