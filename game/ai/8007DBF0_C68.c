/* 8007DBF0: built-in program C68 */
extern ? D_800282D8;
extern s16 D_800285D8;
extern ? D_800286D8;
extern s16 D_800289D8;

void AI_C68(struct Entity *e) {
    s16 temp_v0;
    s16 temp_v0_2;
    s32 var_v0;
    s32 var_v1;
    u8 temp_a1;
    u8 temp_v0_3;
    u8 temp_v1;

    temp_v1 = e->bytes[0];
    switch (temp_v1) {
    case 0:
        e->bytes[0] = 1;
        e->ai[1] = 0x180;
        e->delay = e->px - (D_800285D8 * 0x1400);
        e->item_state = e->py - (D_800289D8 * 0x1400);
        /* fallthrough */
    case 1:
        temp_v0 = ((u16) e->ai[1] + 4) & 0x1FF;
        e->ai[1] = temp_v0;
        e->px = e->delay + (*(&D_800282D8 + (temp_v0 * 2)) * 0x1400);
        e->py = e->item_state + (*(&D_800286D8 + ((u16) e->ai[1] * 2)) * 0x1400);
        if (select(e, e->ref_id - 1) == 0) {
            e->bytes[1] = 2;
            e->bytes[0] += 1;
            play_sound(0x78);
            return;
        }
    default:
        return;
    case 2:
        temp_v0_2 = ((u16) e->ai[1] + 4) & 0x1FF;
        temp_a1 = e->bytes[1] - 1;
        e->bytes[1] = temp_a1;
        e->ai[1] = temp_v0_2;
        e->px = e->delay + (*(&D_800282D8 + (temp_v0_2 * 2)) * 0x1400);
        e->py = e->item_state + (*(&D_800286D8 + ((u16) e->ai[1] * 2)) * 0x1400);
        if (!(temp_a1 & 0xFF)) {
            e->target_anim = 3;
            e->bytes[1] = 0x50;
            e->bytes[0] += 1;
            e->target_dir = (0x18 - ((u16) e->ai[1] >> 4)) & 0x1F;
            return;
        }
        break;
    case 3:
        temp_v0_3 = e->bytes[1] - 1;
        e->bytes[1] = temp_v0_3;
        if ((e->force_adjusted != 0) || !(temp_v0_3 & 0xFF)) {
            play_sound(0xE1);
            e->target_anim = 2;
            e->flags |= 0x100;
            e->bytes[0] += 1;
            return;
        }
        break;
    case 4:
        var_v0 = e->px - g_ent->px;
        if (var_v0 < 0) {
            var_v0 = -var_v0;
        }
        var_v1 = e->py - g_ent->py;
        if (var_v0 <= 0x2FFFFF) {
            if (var_v1 < 0) {
                var_v1 = -var_v1;
            }
            if (var_v1 > 0x1FFFFF) {
                goto block_16;
            }
        } else {
block_16:
            e->flags = (e->flags & ~2) | 0x81;
            e->bytes[0] += 1;
            return;
        }
        break;
    case 5:
        if ((e->target_anim == 4) && (e->anim_done != 0)) {
            if ((u8) e->bytes[2] >= 4U) {
                play_sound(0x2E);
                destroy_entity(e, 0xA);
                return;
            }
            e->target_anim = 2;
        }
        break;
    }
}
