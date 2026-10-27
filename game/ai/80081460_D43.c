/* 80081460: built-in program D43 */
void AI_D43(struct Entity *e) {
    e->fz = 0;
    e->pafy = 0;
    e->pafx = 0;
    if (take_hit(e) != 0) {
        e->bytes[3] = 1;
    }
    e->target_anim = 6;
}
