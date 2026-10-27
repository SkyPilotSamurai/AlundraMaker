/* 80080EE0: built-in program D24 */
void AI_D24(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 7;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
}
