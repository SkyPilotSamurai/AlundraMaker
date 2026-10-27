/* 80080708: built-in program D10 */
void AI_D10(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 6;
    e->target_dir = dir_from_delta(e->px - g_ent->px, e->py - g_ent->py);
    if ((u32) (e->sprite_index - 0x1C4) < 2U) {
        play_sound(0x41);
    }
}
