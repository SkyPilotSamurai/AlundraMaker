/* 80081808: built-in program E9 */
void AI_E9(struct Entity *e) {
    s32 sp18;
    s32 sp1C;
    s32 temp_hi;
    s32 temp_hi_2;
    s32 temp_lo;
    s32 temp_lo_2;
    s32 temp_v1;
    s32 temp_v1_2;
    s32 temp_v1_4;
    s32 var_s1;
    s32 var_s4;
    s32 var_s4_2;
    struct Effect *temp_v0;
    struct Effect *temp_v0_2;
    u32 temp_v1_3;
    u32 temp_v1_5;

    if (e->target_anim == 1) {
        temp_v1 = e->slope_now;
        if ((temp_v1 == 1) || (temp_v1 == 4)) {
            destroy_entity(e, 6);
        }
        if (e->anim_done == 1) {
            destroy_entity(e, -1);
            return;
        }
        if (!(e->frame_counter & 7)) {
            temp_v1_2 = (u32) (e->sprite_index - 0xB) < 2U;
            var_s4 = 0x12;
            if (temp_v1_2 != 0) {
                var_s4 = 0x11;
            }
            temp_v0 = spawn_effect(0, var_s4, 0, e->px, e->py, e->pz + (temp_v1_2 << 0x13));
            if (temp_v0 != NULL) {
                temp_v1_3 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                temp_lo = temp_v1_3 * 0x7D2B89DD;
                temp_hi = MULTU_HI(temp_v1_3, 0x30001);
                g_rng_seed = temp_v1_3;
                sp18 = temp_v1_3 * 0x30001;
                sp1C = temp_hi;
                temp_v0->vz = 0x20000;
                g_rng_seed = temp_lo + 0xE06A02E7;
                temp_v0->vx = (temp_hi >> 0) + 0xFFFE8000;
                temp_v0->vy = ((temp_lo + 0xE06A02E7) / 32768) + 0xFFFF0000;
            }
        }
    } else {
        var_s4_2 = 0x12;
        if ((u32) (e->sprite_index - 0xB) < 2U) {
            var_s4_2 = 0x11;
        }
        temp_v1_4 = e->slope_now;
        if ((temp_v1_4 == 1) || (var_s1 = 0, (temp_v1_4 == 4))) {
            destroy_entity(e, 6);
            return;
        }
        do {
            temp_v0_2 = spawn_effect(0, var_s4_2, 0, e->px, e->py, e->pz);
            if (temp_v0_2 != NULL) {
                temp_v1_5 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                temp_lo_2 = temp_v1_5 * 0x7D2B89DD;
                temp_hi_2 = MULTU_HI(temp_v1_5, 0x60001);
                sp18 = temp_v1_5 * 0x60001;
                sp1C = temp_hi_2;
                g_rng_seed = temp_v1_5;
                g_rng_seed = temp_lo_2 + 0xE06A02E7;
                temp_v0_2->vx = (temp_hi_2 >> 0) + 0xFFFD0000;
                temp_v0_2->vy = ((temp_lo_2 + 0xE06A02E7) / 16384) + 0xFFFE0000;
            }
            var_s1 += 1;
        } while (var_s1 < 5);
        e->target_anim = 1;
        e->flags = (e->flags | 0x40) & ~0x30;
    }
}
