/* 8008100C: built-in program D28 */
void AI_D28(struct Entity *e) {
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 7;
}
