/* 800810E0: built-in program D32 */
void AI_D32(struct Entity *e) {
    if ((*e->touching->attack_addr & 0xF) == 4) {
        e->target_anim += 1;
        e->flags |= 0x40;
    }
}
