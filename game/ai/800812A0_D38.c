/* 800812A0: built-in program D38 */
void AI_D38(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 2;
}
