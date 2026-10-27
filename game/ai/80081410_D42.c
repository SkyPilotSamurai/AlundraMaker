/* 80081410: built-in program D42 */
void AI_D42(struct Entity *e) {
    if (e->hp != 0) {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 1;
    }
}
