/* 80080988: built-in program D14 */
void AI_D14(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 5;
}
