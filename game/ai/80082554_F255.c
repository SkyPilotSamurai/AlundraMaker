/* 80082554: built-in program F255 */
s32 func_80034458(s32);                             /* extern */
? func_8003B67C(struct Entity *);                   /* extern */
s32 func_80045F8C();                                /* extern */
? func_8004608C(s32, ?);                            /* extern */
? func_8004AD18(?);                                 /* extern */
s32 func_80083FC4(?);                               /* extern */
extern s32 D_80029B70;
extern s32 D_8009C6C0;
extern ? D_800C7DE9;

void AI_F255(struct Entity *e) {
    ? var_a0;
    s32 temp_s2;
    s32 temp_v0_2;
    struct Entity *temp_v0;

    if ((g_mode_flags == 0) && (g_warp_request == 0) && (g_ent->carried == NULL) && (func_80045F8C() == 0)) {
        temp_s2 = e->contents_item;
        var_a0 = 0x48;
        if ((temp_s2 != 0) && (e->target_anim == 0)) {
            e->target_anim = 2;
            temp_v0 = spawn_warp_entity(e, 0, temp_s2 + 0x1E, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x100000), /* extra? */ 0);
            var_a0 = 0x49;
            if (temp_v0 != NULL) {
                func_8003B67C(e);
                temp_v0->fz = 0x8000;
                temp_v0->delay = 0x40;
                temp_v0->frozen = 0;
                temp_v0->unk274 = 2;
                temp_v0->item_state = 0;
                temp_v0->unk280 = e;
                temp_v0->flags &= ~0x180;
                temp_v0_2 = func_80034458(temp_s2);
                temp_v0->unk284 = temp_v0_2;
                if ((temp_v0_2 != 0) && (*(&D_800C7DE9 + (temp_s2 * 8)) == 0) && ((D_80029B70 != 0) || (D_8009C6C0 != 0))) {
                    temp_v0->unk288 = 1;
                    func_8004AD18(0);
                    return;
                }
                temp_v0->unk288 = 0;
                return;
            }
        }
        func_8004608C(func_80083FC4(var_a0), 0);
    }
}
