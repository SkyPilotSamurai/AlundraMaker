/* 8007FDC0: built-in program C84 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
? func_80083394(struct Entity *, u8, struct Entity *); /* extern */

void AI_C84(struct Entity *e) {
    s16 var_v0;
    s32 *var_v1;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a2_2;
    s32 temp_a2_3;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 var_a0;
    s32 var_a2;
    struct Entity *temp_a2;
    struct Entity *var_a1;
    u16 temp_v0_2;
    u16 temp_v0_3;
    u8 temp_a1;
    u8 temp_v0;
    u8 temp_v1;

    temp_a2 = e->parent;
    if ((u16) temp_a2->ai[4] != 0) {
        temp_a2->ai[4] = 0;
        e->target_anim = 3;
    }
    temp_a1 = temp_a2->bytes[0];
    temp_a2->px = e->px;
    temp_a2->py = e->py + 0xFFF00000;
    if (temp_a1 != temp_a2->bytes[2]) {
        temp_a2->pz -= 0x8000;
        temp_a2->bytes[2] += 1;
    } else {
        temp_v0 = temp_a2->bytes[1];
        if (temp_v0 != 0) {
            temp_a2->bytes[1] = temp_v0 - 1;
        } else {
            temp_a0 = temp_a2->pz;
            if (temp_a0 != (e->pz + 0x300000)) {
                temp_a2->pz = temp_a0 + 0x8000;
                temp_a2->bytes[0] -= 1;
                temp_a2->bytes[2] -= 1;
            }
        }
    }
    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394(e, temp_a1, temp_a2);
            return;
        }
        e->target_anim = 4;
        e->flags |= 0x40;
        remove_entity(temp_a2);
        e->bi_c = 0;
        return;
    }
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {
    case 5:
        var_v0 = 0x3C;
        if (e->anim_done != 0) {
            e->target_anim = 0;
            temp_a2->target_anim = 0;
block_46:
            e->ai[1] = var_v0;
        }
    default:
        return;
    case 0:
        var_a2 = 0;
        var_a0 = 0;
        var_a1 = g_ent;
        var_v1 = &g_ent->sprite_index;
loop_19:
        if (((u32) (var_v1->unk-58 - 2) >= 2U) || (var_v1->unk-48 != 0) || (e == var_a1) || (var_v1->unk0 != 0x1D8)) {
            var_a0 += 1;
            var_v1 += 0x294;
            var_a1 += 0x294;
            if (var_a0 != 0x40) {
                goto loop_19;
            }
        } else {
            var_a2 = 1;
        }
        if (var_a2 != 0) {
            temp_a2_2 = var_a1->mpx;
            temp_v1_3 = e->mpx;
            temp_a0_2 = temp_a2_2 - temp_v1_3;
            if (temp_a0_2 >= 0) {
                if (temp_a0_2 < (e->sizex + 1)) {
                    goto block_29;
                }
                goto block_34;
            }
            if ((temp_v1_3 - temp_a2_2) < (var_a1->sizex + 1)) {
block_29:
                temp_a2_3 = var_a1->mpy;
                temp_v1_4 = e->mpy;
                temp_a0_3 = temp_a2_3 - temp_v1_4;
                if (temp_a0_3 >= 0) {
                    if (temp_a0_3 < (e->sizey + 1)) {
                        goto block_33;
                    }
                    goto block_34;
                }
                if ((temp_v1_4 - temp_a2_3) < (var_a1->sizey + 1)) {
block_33:
                    e->target_anim = 1;
                    e->target_dir = dir_from_delta(e->px - var_a1->px, e->py - var_a1->py);
                    var_v0 = 0x1E;
                    goto block_46;
                }
                goto block_34;
            }
            goto block_34;
        }
block_34:
        temp_v0_2 = (u16) e->ai[1];
        var_v0 = temp_v0_2 - 1;
        if (temp_v0_2 == 0) {
            start_moving(e, 1, 0x3C, 0x46);
            if (e->bytes[0] != 0) {
                e->bytes[0] = 0;
                e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                return;
            }
        } else {
            goto block_46;
        }
        break;
    case 1:
        temp_v0_3 = (u16) e->ai[1];
        if (temp_v0_3 != 0) {
            var_v0 = temp_v0_3 - 1;
        } else {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo + 0xE06A02E7;
            var_v0 = ((temp_lo + 0xE06A02E7) / MULHI_31) + 0x3C;
        }
        goto block_46;
    case 2:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            return;
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            if (temp_a2->bytes[3] != 0) {
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->bytes[3] = 1;
                e->target_anim = 0;
                e->flags &= ~3;
                return;
            }
            temp_lo_2 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            temp_a2->target_anim = 0;
            e->damaged_tick = 0x5A;
            temp_a2->damaged_tick = 0x5A;
            g_rng_seed = temp_lo_2 + 0xE06A02E7;
            e->bytes[0] = 1;
            var_v0 = ((temp_lo_2 + 0xE06A02E7) / MULHI_31) + 0x14;
            goto block_46;
        }
        break;
    }
}
