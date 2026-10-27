/* 80081518: built-in program D45 */
void AI_D45(struct Entity *e) {
    if ((*e->touching->attack_addr & 0xF) == 2) {
        e->target_anim = 4;
        e->bytes[2] += 1;
    }
}
