/* 8008109C: built-in program D31 */
void AI_D31(struct Entity *e) {
    if ((*e->touching->attack_addr & 0xF) == 2) {
        e->target_anim += 1;
        e->flags |= 0x40;
    }
}
