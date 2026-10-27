/* 80081164: built-in program D34 */
void AI_D34(struct Entity *e) {
    if ((*e->touching->attack_addr & 0xF) == 6) {
        e->target_anim = 1;
        e->flags = (e->flags | 0x46) & ~0x80;
    }
}
