/* 800640C4: built-in program C89 */
/* x / MULHI_n = hi(x * n) = (x * n) >> 32 (rnd(n) when x is the new seed) */
/* rel_tile(e, &spX) fills spX..: |dx| |dy| |dz| dx dy dz (tiles, tiles, 16.16 height); the port returns that list */
? func_80083324(?, ?, ?, ?);                        /* extern */
extern ? D_80023654;
extern ? D_80023694;
extern ? D_80026C98;
extern ? D_80026CA0;
extern ? D_800282D8;
extern ? D_800286D8;

void AI_C89(struct Entity *e) {
    s32 sp20;
    s32 sp38;
    s32 sp3C;
    s16 temp_v0_6;
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a0_3;
    s32 temp_a0_4;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_a1_4;
    s32 temp_a2;
    s32 temp_a2_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_lo_3;
    s32 temp_lo_4;
    s32 temp_v0;
    s32 temp_v0_4;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_3;
    s32 temp_v1_4;
    s32 temp_v1_5;
    s32 var_v0;
    s32 var_v0_10;
    s32 var_v0_11;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v0_7;
    s32 var_v0_8;
    s32 var_v0_9;
    s32 var_v1;
    s32 var_v1_2;
    struct Entity *temp_s3;
    struct Entity *temp_v0_2;
    u16 temp_v0_3;
    u16 temp_v0_5;
    u32 temp_a1;
    u32 temp_t0;
    u8 temp_s2;
    void *temp_s1;

    temp_a0 = e->target_anim;
    temp_s3 = e->parent;
    if (temp_a0 != 9) {
        if ((u32) (temp_a0 - 0xA) < 6U) {
            if (temp_s3->hp == 0) {
                destroy_entity(e, -1);
                return;
            }
            if (e->on_ground != 0) {
                play_sound(0x19D);
                e->target_anim = 9;
                e->flags |= 0x40;
                func_80083324(0x600000, 2, 0, 1);
                return;
            }
            if ((e->bytes[0] == 1) && (temp_a0 == 0xF)) {
                if (e->pz >= (temp_s3->pz + 0x01000000)) {
                    temp_lo = g_rng_seed * 0x7D2B89DD;
                    temp_v1 = temp_lo + 0xE06A02E7;
                    temp_lo_2 = temp_v1 * 0x7D2B89DD;
                    temp_a1 = temp_lo_2 + 0xE06A02E7;
                    temp_lo_3 = temp_a1 * 0x7D2B89DD;
                    temp_lo_4 = (temp_lo_3 + 0xE06A02E7) * 0x7D2B89DD;
                    sp38 = temp_v1 * 0x18;
                    sp3C = (temp_lo + 0xE06A02E7) / MULHI_24;
                    temp_t0 = temp_lo_4 + 0xE06A02E7;
                    e->target_anim = 0xA;
                    e->flags |= 0x100;
                    g_rng_seed = temp_a1;
                    g_rng_seed = temp_t0;
                    sp38 = temp_t0 * 5;
                    sp3C = (temp_lo_4 + 0xE06A02E7) / MULHI_5;
                    e->px = (((temp_lo + 0xE06A02E7) / MULHI_24) * 0xC0000) + ((((temp_lo_2 + 0xE06A02E7) / MULHI_7) << 0x10) + 0x01E00000);
                    e->py = (((temp_lo_3 + 0xE06A02E7) / 268435456) << 0x13) + ((((temp_lo_4 + 0xE06A02E7) / MULHI_5) << 0x10) + 0x02800000);
                }
            }
            if (e->bytes[0] == 2) {
                e->pafx = (*(&D_80023654 + (e->target_dir * 2)) * (e->bytes[1] << 0xB)) / 11;
                var_v0 = (*(&D_80023694 + (e->target_dir * 2)) * (e->bytes[1] << 0xB)) / 11;
                goto block_122;
            }
        } else {
            rel_tile(e, &sp20);
            temp_s2 = e->bytes[0];
            temp_v0 = temp_s2 * 0x24;
            temp_s1 = temp_v0 + 0x80124698;
            if (temp_s3->hp == 0) {
                e->target_anim = 7;
                e->flags |= 0x40;
                if (temp_s1->unk18 != 0) {
                    g_ent->px = e->px;
                    g_ent->target_anim = 0;
                    g_mode_flags &= ~0x20;
                    g_ent->py = e->py;
                    temp_s1->unk18 = 0;
                }
            } else {
                temp_a1_2 = temp_s1->unk18;
                if ((temp_a1_2 == 2) && (g_ent->on_ground != 0)) {
                    if (g_ent->target_anim == 0x1C) {
                        if (g_ent->anim_done != 0) {
                            if (e->bytes[2] == 0) {
                                *(s32 *)0x801F94D0 = 1;
                                *(s32 *)0x801F94DC = 1;
                                *(s32 *)0x801F94E0 = 1;
                                *(s32 *)0x801F94D4 = temp_a1_2;
                                *(s32 *)0x801F94D8 = temp_a1_2;
                                temp_v0_2 = spawn_warp_entity(e, 1, e->sprite_index - 0x100, g_ent->px, /* extra? */ g_ent->py, /* extra? */ g_ent->pz, /* extra? */ 0);
                                temp_v0_2->target_anim = 0x11;
                                *(struct Entity **)0x801246E0 = temp_v0_2;
                                temp_v0_2->bi_c = 0;
                                temp_v0_2->flags = (temp_v0_2->flags | 2) & ~0x80;
                                g_ent->anim_flags &= ~0x40;
                                e->bytes[2] = 1;
                            } else if (g_ent->damaged_tick != 0) {
                                remove_entity(*(void *)0x801246E0);
                                e->bytes[2] = 0;
                                g_ent->target_anim = 0x39;
                                g_ent->target_dir = 0x10;
                            }
                        }
                    } else if ((g_ent->target_anim == 0x4E) && (g_ent->anim_done != 0)) {
                        *(void *)0x801F94D0 = 0;
                        g_mode_flags &= ~0x20;
                        if (g_ent->hp != 0) {
                            g_ent->target_anim = 0;
                        }
                        temp_s1->unk18 = 0;
                    }
                }
                if (e->bytes[1] == 0) {
                    temp_s1->unkC = 0x02A00000;
                    temp_s1->unk8 = (s32) *(&D_80026C98 + (temp_s2 * 4));
                    e->bytes[1] = 1;
                }
                temp_v1_2 = e->target_anim;
                switch (temp_v1_2) {
                case 0:
                    temp_v0_3 = (u16) e->ai[1];
                    if (temp_v0_3 != 0) {
                        e->ai[1] = temp_v0_3 - 1;
                    }
                    temp_v0_4 = (e->delay + *(&D_80026CA0 + (temp_s2 * 4))) & 0x1FF;
                    e->delay = temp_v0_4;
                    e->px = temp_s1->unk8 + (*(&D_800282D8 + (temp_v0_4 * 2)) * 0x1200);
                    e->py = temp_s1->unkC + (*(&D_800286D8 + (e->delay * 2)) * 0x1200);
                    temp_s1->unk10 = (s32) e->px;
                    temp_s1->unk14 = (s32) e->py;
                    if ((*(s32 *)0x801E6378 & 2) && (sp24 < 3) && (sp20 < 3) && ((u16) e->ai[1] == 0) && ((((temp_s2 ^ 1) * 0x24) + 0x80120000)->unk46B0 == 0)) {
                        e->target_anim = 0x10;
                        temp_s1->unk1C = (s32) g_ent->px;
                        temp_s1->unk20 = (s32) g_ent->py;
                    }
                default:
block_119:
                    var_v0_2 = *(0x80124698 + temp_v0);
                    if (var_v0_2 != 0) {
block_120:
                        e->pafx = var_v0_2;
                    }
                    break;
                case 16:
                    if (e->anim_done != 0) {
                        e->target_anim = 3;
                        var_v0_3 = temp_s1->unk1C - e->px;
                        if (var_v0_3 < 0) {
                            var_v0_3 += 0xF;
                        }
                        *(0x80124698 + temp_v0) = (s32) (var_v0_3 >> 4);
                        temp_s1->unk4 = (s32) ((s32) (temp_s1->unk20 - e->py) / 16);
block_116:
                        e->fz = -0x40000;
                    }
                    goto block_119;
                case 3:
                    temp_v0_5 = (u16) e->ai[1];
                    temp_v0_6 = temp_v0_5 - 1;
                    if (temp_v0_5 != 0) {
                        e->ai[1] = temp_v0_6;
                        if (!(temp_v0_6 & 0xFFFF)) {
                            e->target_anim = 2;
                            var_v0_4 = 0x20000;
block_101:
                            e->fz = var_v0_4;
                            var_v0_5 = temp_s1->unk10 - e->px;
                            if (var_v0_5 < 0) {
                                var_v0_5 += 0xF;
                            }
                            *(0x80124698 + temp_v0) = (s32) (var_v0_5 >> 4);
                            temp_s1->unk4 = (s32) ((s32) (temp_s1->unk14 - e->py) / 16);
                        }
                    } else {
                        temp_v1_3 = e->mpx;
                        temp_a0_2 = g_ent->mpx - temp_v1_3;
                        if (temp_a0_2 >= 0) {
                            if (temp_a0_2 < (e->sizex + 1)) {
                                goto block_52;
                            }
                            goto block_66;
                        }
                        if ((temp_v1_3 - g_ent->mpx) < (g_ent->sizex + 1)) {
block_52:
                            temp_v1_4 = e->mpy;
                            temp_a0_3 = g_ent->mpy - temp_v1_4;
                            if (temp_a0_3 >= 0) {
                                if (temp_a0_3 < (e->sizey + 1)) {
                                    goto block_56;
                                }
                                goto block_66;
                            }
                            if ((temp_v1_4 - g_ent->mpy) < (g_ent->sizey + 1)) {
block_56:
                                temp_v1_5 = e->mpz;
                                temp_a0_4 = g_ent->mpz - temp_v1_5;
                                if (temp_a0_4 >= 0) {
                                    if (temp_a0_4 < (e->sizez + 1)) {
                                        goto block_60;
                                    }
                                    goto block_66;
                                }
                                if ((temp_v1_5 - g_ent->mpz) < (g_ent->sizez + 1)) {
block_60:
                                    if (!(g_ent->anim_flags & 0x40) && (g_ent->damaged_tick == 0) && ((((temp_s2 ^ 1) * 0x24) + 0x80120000)->unk46B0 == 0)) {
                                        e->target_anim = 4;
                                        e->fz = 0x20000;
                                        e->flags &= ~1;
                                        var_v0_6 = temp_s1->unk8 - e->px;
                                        if (var_v0_6 < 0) {
                                            var_v0_6 += 0x1F;
                                        }
                                        *(0x80124698 + temp_v0) = (s32) (var_v0_6 >> 5);
                                        temp_s1->unk4 = (s32) ((s32) (temp_s1->unkC - e->py) / 32);
                                        g_ent->target_anim = 0x56;
                                        g_mode_flags |= 0x20;
                                        g_ent->flags &= ~0x108;
                                        temp_s1->unk18 = 1;
                                    } else {
                                        goto block_66;
                                    }
                                } else {
                                    goto block_66;
                                }
                            } else {
                                goto block_66;
                            }
                        } else {
block_66:
                            if ((e->collided_z != 0) || (e->pz <= 0xA00000)) {
                                e->ai[1] = 0x14;
                                e->fz = 0;
                                temp_s1->unk4 = 0;
                                *(0x80124698 + temp_v0) = 0;
                            }
                        }
                    }
                    goto block_119;
                case 2:
                    if ((u32) (e->pz + 0xFF200000) <= 0x80000U) {
                        e->fz = 0;
                    }
                    temp_a2 = e->px - temp_s1->unk10;
                    temp_a1_3 = e->py - temp_s1->unk14;
                    var_v0_7 = temp_a2;
                    if (temp_a2 < 0) {
                        var_v0_7 = -var_v0_7;
                    }
                    if (var_v0_7 <= 0xBFFFF) {
                        *(0x80124698 + temp_v0) = 0;
                    }
                    var_v1 = temp_a1_3;
                    if (temp_a1_3 < 0) {
                        var_v1 = -var_v1;
                    }
                    if (var_v1 <= 0x7FFFF) {
                        temp_s1->unk4 = 0;
                    }
                    if (e->fz == 0) {
                        var_v0_2 = *(0x80124698 + temp_v0);
                        if (var_v0_2 == 0) {
                            if (temp_s1->unk4 == 0) {
                                e->ai[1] = 0x78;
                                e->target_anim = 0;
                                temp_s1->unk8 = (s32) (*(&D_80026C98 + (temp_s2 * 4)) + (e->px - temp_s1->unk10));
                                temp_s1->unkC = (s32) ((e->py - temp_s1->unk14) + 0x02A00000);
                            }
                            goto block_119;
                        }
                        goto block_120;
                    }
                    goto block_119;
                case 4:
                    if (e->pz > 0x018FFFFF) {
                        e->fz = 0;
                    }
                    temp_a2_2 = e->px - temp_s1->unk8;
                    temp_a1_4 = e->py - temp_s1->unkC;
                    var_v0_8 = temp_a2_2;
                    if (temp_a2_2 < 0) {
                        var_v0_8 = -var_v0_8;
                    }
                    if (var_v0_8 <= 0xBFFFF) {
                        *(0x80124698 + temp_v0) = 0;
                    }
                    var_v1_2 = temp_a1_4;
                    if (temp_a1_4 < 0) {
                        var_v1_2 = -var_v1_2;
                    }
                    if (var_v1_2 <= 0x7FFFF) {
                        temp_s1->unk4 = 0;
                    }
                    if (e->fz == 0) {
                        var_v0_9 = *(0x80124698 + temp_v0);
                        if (var_v0_9 == 0) {
                            if (temp_s1->unk4 == 0) {
                                e->target_anim = 5;
                                e->flags |= 1;
                                temp_s1->unk18 = 2;
                                g_ent->target_anim = 0x31;
                                g_ent->target_dir = 0;
                                g_ent->flags |= 0x108;
                                g_ent->px = e->px;
                                g_ent->py = e->py;
                            }
                            goto block_97;
                        }
                    } else {
block_97:
                        var_v0_9 = *(0x80124698 + temp_v0);
                    }
                    g_ent->pafx = var_v0_9;
                    g_ent->pafy = temp_s1->unk4;
                    g_ent->fz = e->fz;
                    goto block_119;
                case 5:
                    if (e->anim_done != 0) {
                        e->target_anim = 2;
                        var_v0_4 = -0x40000;
                        goto block_101;
                    }
                    goto block_119;
                case 6:
                    temp_s1->unk4 = 0;
                    *(0x80124698 + temp_v0) = 0;
                    if (e->anim_done != 0) {
                        if (e->bytes[3] != 0) {
                            e->target_anim = 7;
                            e->flags |= 0x40;
                            if (temp_s2 == 0) {
                                temp_s3->delay = 0x708;
                            } else {
                                temp_s3->item_state = 0x708;
                            }
                        } else {
                            var_v0_10 = temp_s1->unk10 - e->px;
                            if (var_v0_10 < 0) {
                                var_v0_10 += 0xF;
                            }
                            *(0x80124698 + temp_v0) = (s32) (var_v0_10 >> 4);
                            var_v0_11 = temp_s1->unk14 - e->py;
                            if (var_v0_11 < 0) {
                                var_v0_11 += 0xF;
                            }
                            temp_s1->unk4 = (s32) (var_v0_11 >> 4);
                            e->target_anim = 2;
                            if (e->pz <= 0xDFFFFF) {
                                e->fz = 0x20000;
                            }
                            if (e->pz > 0xE7FFFF) {
                                goto block_116;
                            }
                        }
                    }
                    goto block_119;
                case 8:
                    e->px = temp_s1->unk8 + (*(&D_800282D8 + (e->delay * 2)) * 0x1200);
                    e->pz = 0xE00000;
                    e->py = temp_s1->unkC + (*(&D_800286D8 + (e->delay * 2)) * 0x1200);
                    if (e->anim_done != 0) {
                        e->target_anim = 0;
                    }
                    goto block_119;
                }
                var_v0 = temp_s1->unk4;
                if (var_v0 != 0) {
block_122:
                    e->pafy = var_v0;
                }
            }
        }
    }
}
