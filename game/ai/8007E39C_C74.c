/* 8007E39C: built-in program C74 */
void AI_C74(struct Entity *e) {
    s32 sp18;
    s32 sp1C;
    s32 temp_hi;
    s32 temp_lo;
    s32 temp_v0;
    struct Effect *temp_v0_2;
    u32 temp_v1;

    temp_v0 = e->target_anim;
    switch (temp_v0) {
    case 1:
        if (!(e->frame_counter & 3)) {
            temp_v0_2 = spawn_effect(0, 0xE, 0, e->px, e->py, e->pz);
            if (temp_v0_2 != NULL) {
                temp_v1 = (g_rng_seed * 0x7D2B89DD) + 0xE06A02E7;
                temp_lo = temp_v1 * 0x7D2B89DD;
                temp_hi = MULTU_HI(temp_v1, 0x30001);
                g_rng_seed = temp_v1;
                sp18 = temp_v1 * 0x30001;
                sp1C = temp_hi;
                temp_v0_2->vz = 0x20000;
                g_rng_seed = temp_lo + 0xE06A02E7;
                temp_v0_2->vx = (temp_hi >> 0) + 0xFFFE8000;
                temp_v0_2->vy = ((temp_lo + 0xE06A02E7) / 32768) + 0xFFFF0000;
                return;
            }
        }
    default:
        return;
    case 2:
        e->fz = (s32) (e->unk274 - e->pz) >> 1;
        if (g_ent->riding == e) {
            e->fz = -0x8000;
            e->target_anim = 3;
            return;
        }
        break;
    case 3:
        if (g_ent->riding != e) {
block_13:
            e->target_anim = 2;
            return;
        }
        break;
    case 4:
        if (g_ent->riding != e) {
            if (g_ent->fz > 0) {
                g_ent->fz = 0x98000;
                e->target_anim = 5;
                return;
            }
            goto block_13;
        }
        break;
    case 5:
        e->fz = (s32) (e->unk274 - e->pz) >> 1;
        break;
    }
}
