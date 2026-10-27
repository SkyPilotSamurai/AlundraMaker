/* 80081124: built-in program D33 */
void AI_D33(struct Entity *e) {
    s32 temp_v1;

    temp_v1 = *e->touching->attack_addr & 0xF;
    if (temp_v1 == 2) {
        e->target_anim = temp_v1;
        e->flags |= 0x40;
    }
}
