/* 80081264: built-in program D37 */
void AI_D37(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 1;
}
