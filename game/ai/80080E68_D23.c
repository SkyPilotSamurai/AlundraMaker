/* 80080E68: built-in program D23 */
void AI_D23(struct Entity *e) {
    struct Entity *temp_v1;

    if (take_hit(e) != 0) {
        temp_v1 = e->parent;
        e->bytes[3] = 1;
        temp_v1->bytes[2] -= 1;
    }
    e->target_anim = 5;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
}
