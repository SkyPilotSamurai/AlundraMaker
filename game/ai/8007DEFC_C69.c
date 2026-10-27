/* 8007DEFC: built-in program C69 */
s32 func_80083204(struct Entity *, struct Entity *); /* extern */
extern ? D_80028AF8;

void AI_C69(struct Entity *e) {
    s32 temp_v0;
    s32 temp_v1;

    temp_v1 = e->target_anim;
    switch (temp_v1) {                              /* irregular */
    case 0:
        if ((e->x_collision == g_ent) || (g_ent->x_collision == e)) {
            temp_v0 = e->delay + 1;
            e->delay = temp_v0;
            if (temp_v0 == 0x14) {
                e->delay = 0;
                e->target_anim = 1;
                e->target_dir = (s32) *(&D_80028AF8 + func_80083204(g_ent, e));
                return;
            }
            return;
        }
        e->delay = 0;
        return;
    case 1:
        if (e->force_adjusted != 0) {
            e->target_anim = 0;
        }
        break;
    }
}
