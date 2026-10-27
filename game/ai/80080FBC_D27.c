/* 80080FBC: built-in program D27 */
void AI_D27(struct Entity *e) {
    if (e->target_anim != 4) {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 6;
    }
}
