/* 80073674: built-in program C77 */
void AI_C77(struct Entity *e) {
    s32 temp_v1;

    if (e->target_anim == 0) {
        temp_v1 = e->fz;
        if (temp_v1 >= 0xFFF80000) {
            e->fz = temp_v1 - 0x4000;
        }
    }
}
