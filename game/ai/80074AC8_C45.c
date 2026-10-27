/* 80074AC8: built-in program C45 */
extern ? D_80028AF8;

void AI_C45(struct Entity *e) {
    s16 temp_v0_2;
    s16 temp_v0_5;
    s32 temp_v1;
    struct Entity *temp_v0_3;
    u16 temp_v0;
    u16 temp_v0_4;

    if (*(s32 *)0x801E6378 & 1) {
        e->target_anim = 1;
        e->flags |= 0x40;
        return;
    }
    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 2:
        temp_v0 = (u16) e->ai[1];
        temp_v0_2 = temp_v0 - 1;
        if (temp_v0 == 0) {
            e->ai[1] = 0x30;
            return;
        }
        e->ai[1] = temp_v0_2;
        if (!(temp_v0_2 & 7)) {
            temp_v0_3 = spawn_warp_entity(e, 1, 0xFF, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ (s32) *(&D_80028AF8 + e->anim_quadrant));
            if (temp_v0_3 != NULL) {
                temp_v0_3->target_anim = 3;
                temp_v0_3->bi_e = 0x19;
            }
        }
        if ((u16) e->ai[1] == 0) {
            e->target_anim = 0;
            e->ai[1] = 0x1E;
            return;
        }
        return;
    case 0:
        temp_v0_4 = (u16) e->ai[1];
        temp_v0_5 = temp_v0_4 - 1;
        if ((temp_v0_4 == 0) || (e->ai[1] = temp_v0_5, ((temp_v0_5 & 0xFFFF) == 0))) {
            e->target_anim = 2;
            e->target_dir = dir_from_delta(g_ent->px - e->px, g_ent->py - e->py);
        }
        break;
    }
}
