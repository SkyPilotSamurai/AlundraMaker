/* 8007E594: built-in program C75 */
extern ? D_800204F0;
extern ? D_800206F0;
extern ? D_80023654;
extern ? D_80023694;

void AI_C75(struct Entity *e) {
    s32 temp_a0;
    s32 temp_a0_2;
    s32 temp_a1;
    s32 temp_a2;
    s32 temp_lo;
    s32 temp_v0;
    s32 temp_v1;
    s32 var_a0;
    s32 var_a1;
    s32 var_v0;
    void *temp_v0_2;

    if (!(g_pad_held & 0x20)) {
        e->unk290 = (s32) (e->unk290 - 1);
    }
    temp_v0 = e->unk290;
    if (temp_v0 > 0) {
        temp_a2 = e->unk284;
        temp_a1 = e->unk288;
        temp_a0 = *((temp_a2 * 4) + e->bytes);
        if (temp_a0 >= temp_a1) {
            var_a1 = temp_a1 + (e->item_state + ((temp_a1 < e->unk274) << 6));
            var_v0 = var_a1 < temp_a0;
        } else {
            var_a1 = temp_a1 - e->item_state;
            var_v0 = temp_a0 < var_a1;
        }
        if (var_v0 == 0) {
            var_a1 = temp_a0;
            e->unk284 = (s32) (temp_a2 ^ 1);
        }
        temp_v1 = (e->unk28C + e->unk280) & 0xFF;
        temp_a0_2 = temp_v1 * 2;
        e->unk288 = var_a1;
        e->unk28C = temp_v1;
        e->pafx = (g_ent->px + (*(&D_800204F0 + temp_a0_2) * var_a1 * 3) + g_ent->fx) - e->px;
        e->pafy = (g_ent->py + (*(&D_800206F0 + temp_a0_2) * var_a1 * 2) + g_ent->fy) - e->py;
        e->fz = (g_ent->pz - e->pz) + 0x80000;
        return;
    }
    if (temp_v0 == 0) {
        if ((find_targets(e, 1, *e->attack_addr & 0xF, 0x80142B80, 0x80142C80) != 0) && ((void *)0x80142B80->unk100 < 0x3840)) {
            temp_v0_2 = (void *)0x80142B80->unk0;
            var_a0 = dir_from_delta(temp_v0_2->unk114 - e->px, temp_v0_2->unk118 - e->py) * 2;
        } else {
            temp_lo = g_rng_seed * 0x7D2B89DD;
            g_rng_seed = temp_lo + 0xE06A02E7;
            var_a0 = ((temp_lo + 0xE06A02E7) / 134217728) * 2;
        }
        e->fz = 0xA0000;
        e->unk274 = (s32) (*(&D_80023654 + var_a0) << 8);
        e->flags |= 0x2130;
        e->delay = *(&D_80023694 + var_a0) << 8;
    }
    e->pafx = e->unk274;
    e->pafy = e->delay;
}
