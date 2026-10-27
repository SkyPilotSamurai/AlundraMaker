/* 800813D4: built-in program D41 */
void AI_D41(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 3;
}
