/* 80072164: built-in program C39 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_8004A7B4(?);                                 /* extern */
? func_80083394(struct Entity *);                   /* extern */

void AI_C39(struct Entity *e) {
    s32 sp18;
    s16 temp_v0_3;
    s16 temp_v1_4;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_lo_5;
    s32 temp_lo_6;
    s32 temp_lo_7;
    s32 temp_lo_8;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 temp_v0_5;
    s32 temp_v0_9;
    s32 temp_v1_2;
    s32 var_a0;
    s32 var_v0;
    struct Entity *var_v1;
    u16 temp_v1_3;
    u32 temp_a1;
    u32 temp_a1_2;
    u8 temp_v0_4;
    u8 temp_v0_6;
    u8 temp_v0_7;
    u8 temp_v0_8;
    u8 temp_v1;

    temp_v0 = e->delay;
    temp_v0_2 = temp_v0 - 1;
    if (temp_v0 != 0) {
        e->delay = temp_v0_2;
        if (temp_v0_2 == 0) {
            *(s32 *)0x801F94D0 = 0;
            func_8004A7B4(0x55);
        }
    }
    if (g_ent->cur_anim == 0x5A) {
        if (g_ent->on_ground != 0) {
            g_ent->target_anim = 0x59;
        }
    }
    if ((g_ent->cur_anim == 0x59) && (g_ent->anim_done != 0)) {
        g_ent->target_anim = 0;
    }
    temp_v1 = e->bytes[3];
    if ((temp_v1 != 0) && (e->target_anim == 0)) {
        if (temp_v1 < 4U) {
            func_80083394(e);
            return;
        }
        e->target_anim = 7;
        e->flags |= 0x40;
        return;
    }
    rel_tile(e, &sp18);
    temp_v1_2 = e->target_anim;
    switch (temp_v1_2) {
    case 10:
        if (e->bytes[1] != 0) {
            if ((u16) e->ai[1] == 0) {
                e->ai[1] = 0x3C;
            }
            temp_v0_3 = (u16) e->ai[1] - 1;
            e->ai[1] = temp_v0_3;
            if (!(temp_v0_3 & 0xFFFF)) {
                e->hp += e->hp_max / 10;
                play_sound(0x31);
                spawn_effect(0, 0xE, 0, e->px + 0xFFEC0000, e->py, e->pz + 0x200000);
                spawn_effect(0, 0xE, 0, e->px + 0xFFF00000, e->py, e->pz + 0x3C0000);
                spawn_effect(0, 0xE, 0, e->px, e->py, e->pz + 0x460000);
                spawn_effect(0, 0xE, 0, e->px + 0x100000, e->py, e->pz + 0x400000);
                spawn_effect(0, 0xE, 0, e->px + 0x140000, e->py, e->pz + 0x1C0000);
                temp_v0_4 = e->bytes[1] - 1;
                e->bytes[1] = temp_v0_4;
                if (!(temp_v0_4 & 0xFF)) {
                    goto block_24;
                }
            }
        } else {
            if (sees_player(e, &sp18, 2, 6, 0x300000) != 0) {
block_24:
                e->target_anim = 2;
                return;
            }
        default:
            return;
        }
        break;
    case 2:
        if (e->anim_done != 0) {
            e->target_anim = 0;
            return;
        }
        break;
    case 0:
        temp_v1_3 = (u16) e->ai[1];
        temp_v1_4 = temp_v1_3 - 1;
        if (temp_v1_3 != 0) {
            e->ai[1] = temp_v1_4;
            if ((e->item_state == 0) && ((u32) (temp_v1_4 & 0xFFFF) < 0x10U) && (sp18 < 5) && (sp1C < 5)) {
                temp_lo = g_rng_seed * 0x7D2B89DD;
                e->target_anim = 3;
                g_rng_seed = temp_lo + 0xE06A02E7;
                e->item_state = ((temp_lo + 0xE06A02E7) / MULHI_3) + 3;
                return;
            }
        } else {
            temp_v0_5 = e->item_state;
            if (temp_v0_5 != 0) {
                e->item_state = temp_v0_5 - 1;
            }
            e->ai[4] = 0;
            if (sp18 < 3) {
                if (sp1C < 3) {
                    if (sp20 <= 0x100000) {
                        temp_lo_2 = g_rng_seed * 0x7D2B89DD;
                        temp_a1 = temp_lo_2 + 0xE06A02E7;
                        g_rng_seed = temp_a1;
                        temp_lo_3 = temp_a1 * 0x7D2B89DD;
                        if (((temp_lo_2 + 0xE06A02E7) / MULHI_3) == 0) {
                            g_rng_seed = temp_lo_3 + 0xE06A02E7;
                            var_v0 = (temp_lo_3 + 0xE06A02E7) / 134217728;
                        } else {
                            var_v0 = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                        }
                        e->target_dir = var_v0;
                        e->target_anim = 0x12;
                        return;
                    }
                    goto block_43;
                }
                goto block_43;
            }
block_43:
            if ((e->hp_max / 5) >= e->hp) {
                e->target_anim = 0xF;
                return;
            }
            temp_lo_4 = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo_4 + 0xE06A02E7;
            e->bytes[0] = ((temp_lo_4 + 0xE06A02E7) / 1073741824) + 2;
            temp_lo_5 = g_rng_seed * 0x7D2B89DD;
            temp_a1_2 = temp_lo_5 + 0xE06A02E7;
            e->target_anim = 0x13;
            g_rng_seed = temp_a1_2;
            temp_lo_6 = temp_a1_2 * 0x7D2B89DD;
            if (((temp_lo_5 + 0xE06A02E7) / MULHI_3) == 0) {
                g_rng_seed = temp_lo_6 + 0xE06A02E7;
                e->target_dir = (temp_lo_6 + 0xE06A02E7) / 134217728;
                return;
            }
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
            e->ai[4] = 1;
            return;
        }
        break;
    case 19:
        if (e->anim_done != 0) {
            e->target_anim = 0xD;
            return;
        }
        break;
    case 18:
        if (e->anim_done != 0) {
            e->target_anim = 0xB;
            return;
        }
        break;
    case 3:
        if (e->anim_done != 0) {
            e->target_anim = 4;
            return;
        }
        break;
    case 14:
        if (e->on_ground != 0) {
            temp_v0_6 = e->bytes[0];
            temp_v0_7 = temp_v0_6 - 1;
            if ((temp_v0_6 != 0) && (e->bytes[0] = temp_v0_7, ((temp_v0_7 & 0xFF) != 0))) {
                e->target_anim = 0x13;
                if ((u16) e->ai[4] == 0) {
                    e->target_dir += 8;
                    if (e->force_adjusted != 0) {
                        temp_lo_7 = g_rng_seed * 0x7D2B89DD;
                        g_rng_seed = temp_lo_7 + 0xE06A02E7;
                        if (((temp_lo_7 + 0xE06A02E7) / 1073741824) == 0) {
                            e->target_dir = (e->target_dir + 8) & 0x18;
                            return;
                        }
                    }
                } else {
block_80:
                    e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
                    return;
                }
            } else {
block_64:
                e->target_anim = 6;
                return;
            }
        }
        break;
    case 5:
        if (e->on_ground != 0) {
            e->target_anim = 6;
            e->bytes[2] = 5;
            e->delay = 0x32;
            play_sound(0x55);
            *(void *)0x801F94D0 = 1;
            *(s32 *)0x801F94DC = 1;
            *(s32 *)0x801F94E0 = 1;
            *(s32 *)0x801F94D4 = 2;
            *(s32 *)0x801F94D8 = 2;
            return;
        }
        break;
    case 12:
        if (e->on_ground != 0) {
            goto block_64;
        }
        break;
    case 6:
        temp_v0_8 = e->bytes[2];
        if (temp_v0_8 != 0) {
            e->bytes[2] = temp_v0_8 - 1;
            var_a0 = 0;
            var_v1 = g_ent;
            do {
                if (((var_v1 == g_ent) || (temp_v0_9 = var_v1->sprite_index, (temp_v0_9 == 0x16A)) || (temp_v0_9 == 0x173)) && (var_v1->on_ground != 0) && !(var_v1->anim_flags & 0x40) && (var_v1->damaged_tick == 0)) {
                    var_v1->sfy = 0;
                    var_v1->sfx = 0;
                    var_v1->fy = 0;
                    var_v1->fx = 0;
                    var_v1->tfy = 0;
                    var_v1->tfx = 0;
                    if (var_v1 == g_ent) {
                        g_ent->target_anim = 0x5A;
                        var_a0 += 1;
                    } else {
                        var_v1->target_anim = 0xB;
                        goto block_76;
                    }
                } else {
block_76:
                    var_a0 += 1;
                }
                var_v1 += 0x294;
            } while (var_a0 < 0x40);
        }
        if (e->anim_done != 0) {
            e->ai[1] = 0x3C;
            temp_lo_8 = g_rng_seed * 0x7D2B89DD;
            e->target_anim = 0;
            g_rng_seed = temp_lo_8 + 0xE06A02E7;
            if (((temp_lo_8 + 0xE06A02E7) / 1073741824) == 0) {
                goto block_80;
            }
        }
        break;
    case 15:
        if (e->anim_done != 0) {
            e->target_anim = 0xA;
            e->bytes[1] = 4;
            e->ai[1] = 0;
            return;
        }
        break;
    case 9:
        if (e->anim_done != 0) {
            if (e->bytes[3] != 0) {
                *(s32 *)0x801E6378 |= 1;
                e->ai[1] = 0x12C;
                e->ai[5] = 0x1E;
                e->target_anim = 0;
                e->flags &= ~3;
                return;
            }
            e->damaged_tick = 0x5A;
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            e->bytes[2] = 0;
            return;
        }
        break;
    case 17:
        if (e->anim_done != 0) {
            e->target_anim = 0xA;
            e->bytes[1] = 0;
        }
        break;
    }
}
