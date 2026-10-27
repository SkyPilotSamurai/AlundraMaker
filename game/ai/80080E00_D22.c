/* 80080E00: built-in program D22 */
void AI_D22(struct Entity *e) {
    if ((g_cur_map != 0x7B) && (take_hit(e) != 0)) {
        e->bytes[3] = 1;
    }
    e->target_anim = 6;
    e->bytes[1] += 1;
    e->bytes[0] += 1;
}
