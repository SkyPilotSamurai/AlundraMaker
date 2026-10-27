/* 80080BB4: built-in program D20 */
void AI_D20(struct Entity *e) {
    s32 temp_v0;
    s32 temp_v0_2;
    s32 var_v0;
    struct Entity *temp_a0;
    struct Entity *var_s0;
    struct Entity *var_s1;

    var_s0 = e;
    temp_a0 = var_s0->unk284;
    var_s1 = temp_a0;
    if (temp_a0 != NULL) {
        temp_v0 = dir_from_delta(var_s0->px - g_ent->px, var_s0->py - g_ent->py);
        var_s0->target_dir = temp_v0;
        var_s1->target_dir = (0x20 - temp_v0) & 0x1F;
        if (take_hit(var_s0) != 0) {
            var_s0->bytes[3] = 1;
        }
        var_s1->hp = var_s0->hp;
    } else {
        var_s1 = var_s0;
        var_s0 = var_s1->parent;
        temp_v0_2 = dir_from_delta(var_s1->px - g_ent->px, var_s1->py - g_ent->py);
        var_s1->target_dir = temp_v0_2;
        var_s0->target_dir = (0x20 - temp_v0_2) & 0x1F;
        if (take_hit(var_s1) != 0) {
            var_s0->bytes[3] = 1;
        }
        var_s0->hp = var_s1->hp;
    }
    if (var_s0->bytes[2] == 0) {
        var_s0->target_anim = 9;
        var_v0 = 6;
    } else {
        var_s0->target_anim = 6;
        var_v0 = 9;
    }
    var_s1->target_anim = var_v0;
}
