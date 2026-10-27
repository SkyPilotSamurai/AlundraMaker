/* 80081554: built-in program D46 */
void AI_D46(struct Entity *e) {
    s32 var_v0;

    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    var_v0 = 2;
    if (e->sprite_index == 0x1CB) {
        var_v0 = 3;
    }
    e->target_anim = var_v0;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
}
