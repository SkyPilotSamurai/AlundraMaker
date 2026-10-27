/* 80081054: built-in program D30 */
void AI_D30(struct Entity *e) {
    s32 temp_v1;

    temp_v1 = *e->touching->attack_addr & 0xF;
    if ((temp_v1 == 4) || (temp_v1 == 6) || (temp_v1 == 0xA)) {
        e->estatus = 3;
    }
}
