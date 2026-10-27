/* 80080F4C: built-in program D26 */
void AI_D26(struct Entity *e) {
    s32 temp_v1;

    temp_v1 = *e->touching->attack_addr & 0xF;
    if ((temp_v1 == 7) || (temp_v1 == 9)) {
        if (take_hit(e) != 0) {
            e->bytes[3] = 1;
        }
        e->target_anim = 8;
    }
}
