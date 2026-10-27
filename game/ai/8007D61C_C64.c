/* 8007D61C: built-in program C64 */
void AI_C64(struct Entity *e) {
    s32 var_v0;
    void *temp_a0;

    if (select(e, 0xA) != 0) {
        temp_a0 = *(void **)0x8013D488;
        if (g_ent->carried == temp_a0) {
            e->fz = 0;
            e->flags &= ~0x100;
            e->pz = temp_a0->unk11C;
            e->tfx = -g_ent->tfx;
            e->tfy = -g_ent->tfy;
            e->fx = -g_ent->fx;
            e->fy = -g_ent->fy;
            e->sfx = -g_ent->sfx;
            var_v0 = -g_ent->sfy;
        } else {
            e->flags |= 0x100;
            e->pz = temp_a0->unk11C;
            e->tfx = -temp_a0->unkBC;
            e->tfy = -temp_a0->unkC0;
            e->fx = -temp_a0->unkC4;
            e->fy = -temp_a0->unkC8;
            e->sfx = -temp_a0->unkD4;
            var_v0 = -temp_a0->unkD8;
        }
        e->sfy = var_v0;
    }
}
