/* 80071D48: built-in program C79 */
void AI_C79(struct Entity *e) {
    s32 temp_v1;
    u16 temp_v0;

    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 3:
        temp_v0 = (u16) e->ai[1];
        if (temp_v0 != 0) {
            e->ai[1] = temp_v0 - 1;
            return;
        }
        e->target_anim = 0;
        return;
    case 0:
        if ((e->anim_done != 0) || (e->force_adjusted != 0) || (g_ent->touching == e)) {
            e->target_anim = 1;
            e->flags |= 0x40;
        }
        return;
    }
}
