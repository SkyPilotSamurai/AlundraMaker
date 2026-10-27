/* 800809F0: built-in program D16 */
void AI_D16(struct Entity *e) {
    e->bytes[2] = 0;
    if (e->bytes[1] == 0) {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 8;
        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
        return;
    }
    e->target_anim = 0x10;
}
