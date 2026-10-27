/* 80080AD8: built-in program D18 */
void AI_D18(struct Entity *e) {
    struct Entity *temp_v1;

    if (take_hit(e) != 0) {
        temp_v1 = e->parent;
        e->bytes[3] = 1;
        temp_v1->delay -= 1;
    }
    e->target_anim = 2;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
}
