/* 80082238: built-in program E24 */
void AI_E24(struct Entity *e) {
    s32 temp_v1;
    s32 var_s1;
    s32 var_s2;
    struct Entity *temp_v0;
    struct Entity *temp_v1_2;

    temp_v1 = e->target_anim;
    var_s2 = 0;
    if (temp_v1 == 1) {
        if (e->anim_done == temp_v1) {
            destroy_entity(e, -1);
        }
    } else {
        var_s1 = 4;
        do {
            temp_v0 = spawn_warp_entity(e, 1, 0xE3, e->px, /* extra? */ e->py, /* extra? */ (e->pz + 0x20000), /* extra? */ var_s1);
            if (temp_v0 != NULL) {
                temp_v0->target_anim = e->target_anim;
            }
            var_s2 += 1;
            var_s1 += 8;
        } while (var_s2 != 4);
        temp_v1_2 = e->parent;
        if (temp_v1_2->bytes[3] == 0) {
            *(s32 *)0x801F94D0 = 1;
            *(s32 *)0x801F94DC = 1;
            *(s32 *)0x801F94E0 = 1;
            *(s32 *)0x801F94D4 = 2;
            *(s32 *)0x801F94D8 = 2;
            temp_v1_2->item_state = 0x1E;
        }
        e->target_anim = 1;
        e->flags = (e->flags | 0x40) & ~0x30;
    }
}
