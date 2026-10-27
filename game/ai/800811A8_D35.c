/* 800811A8: built-in program D35 */
void AI_D35(struct Entity *e) {
    if (e->bytes[0] == 0) {
        if (take_hit(e) != 0) {
            play_sound(0x123);
            e->bytes[3] = 1;
        } else {
            play_sound(0x11E);
        }
        e->target_anim = 6;
        e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
        return;
    }
    play_sound(0x120);
    e->target_anim = 4;
}
